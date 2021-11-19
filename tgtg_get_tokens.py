# Before running this, make sure that python, pip and tgtg are installed!
# In a command line: pip install tgtg>=0.7.1 (waiting for merge request of tgtg)

from tgtg import TgtgClient

email = "Your TGTG mail"

# Set up a tgtg client, and confirm the mail you received. You got 2 minutes
client = TgtgClient(email=email)

# Necessary to actually get the tokens
client.get_items()

# Print the result!
print("Copy paste this in your configuration.yaml file:")
print("")
print("sensor:")
print("  - platform: tgtg")
print("    username: '" + email + "'")
print("    access_token: '" + client.access_token + "'")
print("    refresh_token: '" + client.refresh_token + "'")
print("    user_id: '" + client.user_id + "'")
print("    scan_interval: 900")
print("")
input("Press enter to quit ...")
