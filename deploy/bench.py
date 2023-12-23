import logging

from paramiko.client import SSHClient

from deploy.instances import ssh_connect, ssh_exec

logger = logging.getLogger(__name__)


def run_benchmarks_standalone(host: str):
    logger.info("Running benchmarks on standalone MySQL")
    with SSHClient() as ssh:
        ssh_connect(ssh, host)

        ssh_exec(ssh, r"""
            sudo apt-get install -y sysbench
            sysbench oltp_read_write --mysql-user=ubuntu --mysql-password=ubuntu --mysql-db=sakila --table-size=20000 --db-driver=mysql prepare
            sysbench oltp_read_write --mysql-user=ubuntu --mysql-password=ubuntu --mysql-db=sakila --table-size=20000 --db-driver=mysql --threads=6 --time=60 --max-requests=0 run > output.txt
            sysbench oltp_read_write --mysql-user=ubuntu --mysql-password=ubuntu --mysql-db=sakila --table-size=20000 --db-driver=mysql cleanup
            """)

    logger.info("Benchmark on standalone MySQL finished")


def run_benchmarks_cluster(host: str):
    logger.info("Running benchmarks on MySQL Cluster")
    with SSHClient() as ssh:
        ssh_connect(ssh, host)

        ssh_exec(ssh, r"""
            sudo apt-get install -y sysbench
            sysbench oltp_read_write --mysql-user=ubuntu --mysql-password=ubuntu --mysql-db=sakila --table-size=20000 --mysql_storage_engine=ndbcluster --db-driver=mysql prepare
            sysbench oltp_read_write --mysql-user=ubuntu --mysql-password=ubuntu --mysql-db=sakila --table-size=20000 --mysql_storage_engine=ndbcluster --db-driver=mysql --threads=6 --time=60 --max-requests=0 run > output.txt
            sysbench oltp_read_write --mysql-user=ubuntu --mysql-password=ubuntu --mysql-db=sakila --table-size=20000 --mysql_storage_engine=ndbcluster --db-driver=mysql cleanup
            """)

    logger.info("Benchmark on MySQL Cluster finished")
