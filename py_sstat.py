from tabulate import tabulate
import subprocess

if __name__ == '__main__':
    output = subprocess.check_output('/opt/slurm/bin/scontrol show nodes --oneliner | head -2', shell=True)

    print(output.decode())
