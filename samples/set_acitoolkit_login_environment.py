import os
import acisampleslib

parser = acisampleslib.get_login_info('A fast way to set APIC login info as Environment variables')
parser.add_argument('-f', '--file', help='The file where the environment variables store.', default='.profile', choices = ['.bashrc', '.bash_profile', '.profile'])

args = parser.parse_args()

f = open(os.environ['HOME']+'/'+args.file, 'r')
lines = f.readlines()
f.close()
f = open(os.environ['HOME']+'/'+args.file, 'w')
for line in lines:
    if 'APIC_URL' in line or 'APIC_LOGIN' in line or 'APIC_PASSWORD' in line:
        continue
    f.write(line)


def write_to_file(key, value):
    f.write("export " + key + '=' + value + '\n')

write_to_file('APIC_LOGIN', args.login)
write_to_file('APIC_PASSWORD', args.password)
write_to_file('APIC_URL', args.url)

f.close()
