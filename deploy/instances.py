import io
import logging
import tarfile
from textwrap import dedent

import backoff
from mypy_boto3_ec2.service_resource import Instance
from paramiko.client import SSHClient, AutoAddPolicy
from paramiko.rsakey import RSAKey
from paramiko.ssh_exception import NoValidConnectionsError

logger = logging.getLogger(__name__)


class SSHExecError(RuntimeError):
    pass


# Commands from DigitalOcean documentation:
# https://www.digitalocean.com/community/tutorials/how-to-create-a-multi-node-mysql-cluster-on-ubuntu-18-04


@backoff.on_exception(backoff.constant, (NoValidConnectionsError, TimeoutError))
def setup_mysql_single(inst: Instance):
    logger.info("Setting up MySQL instance (n=1)")
    with SSHClient() as ssh_cli:
        ssh_connect(ssh_cli, inst.public_ip_address)

        ssh_exec(ssh_cli, r"""
            sudo apt-get update
            sudo apt-get install -y mysql-server
            sudo apt-get install -y unzip
            """)

        wait_mysql(ssh_cli)

        ssh_exec(ssh_cli, r"""
            sudo sed -i "s/bind-address.*/bind-address = 0.0.0.0/" /etc/mysql/mysql.conf.d/mysqld.cnf
            sudo systemctl restart mysql.service
            """)

        wait_mysql(ssh_cli)

        ssh_exec(ssh_cli, r"""
            wget https://downloads.mysql.com/docs/sakila-db.zip
            unzip sakila-db.zip
            sudo mysql -e "CREATE USER 'ubuntu'@'%' IDENTIFIED BY 'ubuntu';"
            sudo mysql -e "GRANT ALL PRIVILEGES ON *.* TO 'ubuntu'@'%' WITH GRANT OPTION;"
            sudo mysql -e "FLUSH PRIVILEGES;"
            sudo mysql -e "SOURCE sakila-db/sakila-schema.sql;"
            sudo mysql -e "SOURCE sakila-db/sakila-data.sql;"
            """)


@backoff.on_exception(backoff.constant, (NoValidConnectionsError, TimeoutError))
def setup_mysql_cluster_manager(manager: Instance, workers: list[Instance]):
    with SSHClient() as ssh_cli:
        ssh_connect(ssh_cli, manager.public_ip_address)

        ssh_exec(ssh_cli, r"""
            sudo add-apt-repository -y universe
            sudo apt update
            sudo apt install -y libaio1 libmecab2 libtinfo5 libncurses5 unzip
            """)

        # Install the manager

        ssh_exec(ssh_cli, rf"""
            mkdir mysql
            cd mysql
            wget https://dev.mysql.com/get/Downloads/MySQL-Cluster-7.6/mysql-cluster-community-management-server_7.6.6-1ubuntu18.04_amd64.deb
            sudo dpkg -i mysql-cluster-community-management-server_7.6.6-1ubuntu18.04_amd64.deb
            sudo mkdir /var/lib/mysql-cluster
            sudo tee /var/lib/mysql-cluster/config.ini <<EOF
            [ndbd default]
            NoOfReplicas=3
            datadir=/usr/local/mysql/data
            
            [ndb_mgmd]
            hostname={manager.private_ip_address}
            datadir=/var/lib/mysql-cluster
            
            [ndbd]
            NodeId=2
            hostname={workers[0].private_ip_address}
            
            [ndbd]
            NodeId=3
            hostname={workers[1].private_ip_address}
            
            [ndbd]
            NodeId=4
            hostname={workers[2].private_ip_address}

            [mysqld]
            hostname={manager.private_ip_address}
            EOF
            """)

        ssh_exec(ssh_cli, r"""
            sudo ndb_mgmd --reload -f /var/lib/mysql-cluster/config.ini --initial
            """)

        ssh_exec(ssh_cli, rf"""
            sudo ufw allow from {manager.private_ip_address}
            sudo ufw allow from {workers[0].private_ip_address}
            sudo ufw allow from {workers[1].private_ip_address}
            sudo ufw allow from {workers[2].private_ip_address}
            """)

        # Install the server/client

        ssh_exec(ssh_cli, rf"""
            mkdir mysql-c
            cd mysql-c
            wget https://dev.mysql.com/get/Downloads/MySQL-Cluster-7.6/mysql-cluster_7.6.6-1ubuntu18.04_amd64.deb-bundle.tar
            tar -xvf mysql-cluster_7.6.6-1ubuntu18.04_amd64.deb-bundle.tar
            sudo dpkg -i mysql-common_7.6.6-1ubuntu18.04_amd64.deb
            sudo dpkg -i mysql-cluster-community-client_7.6.6-1ubuntu18.04_amd64.deb
            sudo dpkg -i mysql-client_7.6.6-1ubuntu18.04_amd64.deb
            DEBIAN_FRONTEND=noninteractive sudo -E dpkg -i mysql-cluster-community-server_7.6.6-1ubuntu18.04_amd64.deb
            sudo dpkg -i mysql-server_7.6.6-1ubuntu18.04_amd64.deb
            sudo tee -a /etc/mysql/my.cnf <<EOF
            [mysqld]
            ndbcluster
            bind-address=0.0.0.0
            ndb-connectstring={manager.private_ip_address}

            [mysql_cluster]
            ndb-connectstring={manager.private_ip_address}
            EOF
            sudo systemctl restart mysql.service
            """)


@backoff.on_exception(backoff.constant, (NoValidConnectionsError, TimeoutError))
def setup_mysql_cluster_worker(manager: Instance, worker: 'Instance', workers: list['Instance']):
    with SSHClient() as ssh_cli:
        ssh_connect(ssh_cli, worker.public_ip_address)

        ssh_exec(ssh_cli, r"""
            sudo add-apt-repository -y universe
            sudo apt update
            sudo apt install -y libaio1 libmecab2 libtinfo5 libclass-methodmaker-perl
            """)

        ssh_exec(ssh_cli, rf"""
            mkdir mysql
            cd mysql
            wget https://dev.mysql.com/get/Downloads/MySQL-Cluster-7.6/mysql-cluster-community-data-node_7.6.6-1ubuntu18.04_amd64.deb
            sudo dpkg -i mysql-cluster-community-data-node_7.6.6-1ubuntu18.04_amd64.deb
            sudo tee -a /etc/my.cnf <<EOF
            [mysql_cluster]
            ndb-connectstring={manager.private_ip_address}
            EOF
            sudo mkdir -p /usr/local/mysql/data
            """)

        ssh_exec(ssh_cli, rf"""
            sudo ufw allow from {manager.private_ip_address}
            sudo ufw allow from {workers[0].private_ip_address}
            sudo ufw allow from {workers[1].private_ip_address}
            sudo ufw allow from {workers[2].private_ip_address}
            """)

        ssh_exec(ssh_cli, r"""
            sudo ndbd
            """)


@backoff.on_exception(backoff.constant, (NoValidConnectionsError, TimeoutError))
def post_setup_mysql_cluster(manager: Instance):
    with SSHClient() as ssh_cli:
        ssh_connect(ssh_cli, manager.public_ip_address)
        ssh_exec(ssh_cli, r"""
            wget https://downloads.mysql.com/docs/sakila-db.zip
            unzip sakila-db.zip
            sudo mysql -e "CREATE USER 'ubuntu'@'%' IDENTIFIED BY 'ubuntu';"
            sudo mysql -e "GRANT ALL PRIVILEGES ON *.* TO 'ubuntu'@'%' WITH GRANT OPTION;"
            sudo mysql -e "FLUSH PRIVILEGES;"
            sudo mysql -e "SOURCE sakila-db/sakila-schema.sql;"
            sudo mysql -e "SOURCE sakila-db/sakila-data.sql;"
            """)


@backoff.on_exception(backoff.constant, (NoValidConnectionsError, TimeoutError, SSHExecError))
def setup_proxy(inst: Instance, manager: Instance, workers: list[Instance]):
    with SSHClient() as ssh_cli:
        ssh_connect(ssh_cli, inst.public_ip_address)

        ssh_exec(ssh_cli, r"""
            sudo snap install docker
            """)

        with ssh_cli.open_sftp() as sftp:
            with io.BytesIO() as f:
                with tarfile.open(fileobj=f, mode='w:gz') as tar:
                    tar.add("pyproject.toml")
                    tar.add("poetry.lock")
                    tar.add("proxy/")
                f.seek(0)
                sftp.putfo(f, "proxy.tar.gz")

        ssh_exec(ssh_cli, rf"""
            rm -rf app && mkdir -p app
            tar xzf proxy.tar.gz -C app/
            cd app
            sudo docker build -t proxy -f proxy/Dockerfile .
            sudo docker run -d -p 80:8080 \
                -e MANAGER_HOST={manager.private_ip_address} \
                -e SLAVE_1_HOST={workers[0].private_ip_address} \
                -e SLAVE_2_HOST={workers[1].private_ip_address} \
                -e SLAVE_3_HOST={workers[2].private_ip_address} \
                proxy
            """)


@backoff.on_exception(backoff.constant, (NoValidConnectionsError, TimeoutError, SSHExecError))
def setup_gatekeeper(inst: Instance, forward_inst: Instance):
    with SSHClient() as ssh_cli:
        ssh_connect(ssh_cli, inst.public_ip_address)

        ssh_exec(ssh_cli, r"""
            sudo snap install docker
            """)

        with ssh_cli.open_sftp() as sftp:
            with io.BytesIO() as f:
                with tarfile.open(fileobj=f, mode='w:gz') as tar:
                    tar.add("pyproject.toml")
                    tar.add("poetry.lock")
                    tar.add("gatekeeper/")
                f.seek(0)
                sftp.putfo(f, "gatekeeper.tar.gz")

        ssh_exec(ssh_cli, rf"""
            rm -rf app && mkdir -p app
            tar xzf gatekeeper.tar.gz -C app/
            cd app
            sudo docker build -t gatekeeper -f gatekeeper/Dockerfile .
            sudo docker run -d -p 80:8080 -e PROXY_HOST={forward_inst.private_ip_address} gatekeeper
            """)


def ssh_connect(cli: SSHClient, ip: str):
    cli.set_missing_host_key_policy(AutoAddPolicy())
    cli.connect(
        hostname=ip,
        username='ubuntu',
        pkey=RSAKey.from_private_key_file('keypair.pem')
    )


def ssh_exec(cli: SSHClient, cmd: str):
    cmd = dedent(cmd)
    logger.info(f"SSH >> {cmd}")
    stdin, stdout, stderr = cli.exec_command(cmd, get_pty=True)
    status = stdout.channel.recv_exit_status()
    if status != 0:
        logger.error(f"SSH error >> {stdout.read().decode().strip()}")
        err = stderr.read().decode().strip()
        logger.error(f"SSH error >> {err}")
        raise SSHExecError(err)


def wait_mysql(cli: SSHClient):
    ssh_exec(cli, r"""
        while ! sudo mysql -e "SHOW DATABASES;"; do
            echo "MySQL is not ready yet. Waiting 1 second..."
            sleep 1
        done
        """)
