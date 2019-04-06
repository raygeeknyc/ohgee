import sys

def generate_conf_header(conf_file):
        conf_file.write(
                '''
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US
#############################
# MAKE THE FOLLOWING CHANGES FOR YOUR OWN NETWORKS
# YOU CAN HAVE AS MANY network= SECTIONS AS YOU WANT
# THE DEVICE WILL CONNECT TO THE FIRST ONE THAT IT FINDS
#############################

###############
# FOR A NETWORK WITH A PASSWORD COPY OR MODIFY THIS ENTRY AS FOLLOWS
#   CHANGE THE ssid= TO YOUR NETWORK NAME, IN THE QUOTES
#   CHANGE THE psk=  TO YOUR NETWORK PASSWORD IN THE QUOTES
###############
                ''')

def generate_conf_footer(conf_file):
        conf_file.write(
                '''
###############
# END OF FILE
###############
                ''')

def generate_open_network(conf_file, ssid):
        stanza = '''
network={
        ''' + 'ssid="{}"'.format(ssid) + '''
        key_mgmt=NONE
}
        '''
        conf_file.write(stanza)

def generate_wpa2_network(conf_file, ssid, psk):
        stanza = '''
network={
        ''' + 'ssid="{}"'.format(ssid) + '''
        key_mgmt=WPA-PSK
        ''' + 'psk="{}"'.format(psk) + '''
}
        '''

        conf_file.write(stanza)

def generate_configuration(networks_filename, conf_filename):
        networks_file = open(networks_filename, 'r')
        conf_file = open(conf_filename, 'w')
        generate_conf_header(conf_file)
        for line in networks_file:
                line = line.strip()
                if len(line) == 0 or line[0] == '#':
                        continue
                tokens=line.split(',')
                if len(tokens) == 1:
                        generate_open_network(conf_file, tokens[0])
                elif len(tokens) == 2:
                        generate_wpa2_network(conf_file, tokens[0], tokens[1])
                else:
                        sys.stderr.write('invalid line "{}"\n'.format(line))
        generate_conf_footer(conf_file)
        networks_file.close()
        conf_file.close()

if len(sys.argv) != 3:
        sys.stderr.write('{} networks_file, conf_file\n'.format(sys.argv[0]))
        sys.exit(255)

generate_configuration(sys.argv[1], sys.argv[2])
sys.exit(0)
