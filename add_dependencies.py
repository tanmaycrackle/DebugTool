import subprocess

with open('requirements.txt', 'r') as file:
    requirements = file.readlines()

for requirement in requirements:
    subprocess.run(['poetry', 'add', requirement.strip()], check=True)
