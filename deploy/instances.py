import logging

import backoff
from mypy_boto3_ec2.service_resource import Instance
from paramiko.client import SSHClient, AutoAddPolicy
from paramiko.rsakey import RSAKey
from paramiko.ssh_exception import NoValidConnectionsError

logger = logging.getLogger(__name__)


@backoff.on_exception(backoff.constant, (NoValidConnectionsError, TimeoutError))
def setup_mysql_single(inst: Instance):
    logger.info("Setting up MySQL instance (n=1)")
    with SSHClient() as ssh_cli:
        ssh_cli.set_missing_host_key_policy(AutoAddPolicy())
        ssh_cli.connect(
            hostname=inst.public_ip_address,
            username='ubuntu',
            pkey=RSAKey.from_private_key_file('keypair.pem')
        )
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


def ssh_exec(cli: SSHClient, cmd: str):
    stdin, stdout, stderr = cli.exec_command(cmd, get_pty=True)
    status = stdout.channel.recv_exit_status()
    logger.info(f"SSH >> {stdout.read().decode().strip()}")
    if status != 0:
        err = stderr.read().decode().strip()
        logger.error(f"SSH >> {err}")
        raise RuntimeError(err)


def wait_mysql(cli: SSHClient):
    ssh_exec(cli, r"""
        while ! sudo mysql -e "SHOW DATABASES;"; do
            echo "MySQL is not ready yet. Waiting 1 second..."
            sleep 1
        done
        """)
