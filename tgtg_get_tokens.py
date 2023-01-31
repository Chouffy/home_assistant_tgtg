# Before running this, make sure that python3, pip and tgtg are installed!
# In a command line: pip install tgtg==0.14.0

from tgtg import TgtgClient

# Input your email here
email = input("Type your email linked to your TGTG account: ")

# Set up a tgtg client
tgtgClient = TgtgClient(email=email)
tgtgClient.get_credentials()

# You should receive an email from TGTG: click the link inside to continue.

# Print the result!
print()
print("Copy-paste this in your configuration.yaml file:")
print("")
print("sensor:")
print("  - platform: tgtg")
print("    email: '" + email + "'")
print("    access_token: '" + tgtgClient.access_token + "'")
print("    refresh_token: '" + tgtgClient.refresh_token + "'")
print("    user_id: '" + tgtgClient.user_id + "'")
print("    cookie: '" + tgtgClient.cookie + "'")
print("    scan_interval: 900")
print("")
input("Press enter to continue ...")
