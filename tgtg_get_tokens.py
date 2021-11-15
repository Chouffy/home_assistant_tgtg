# Before running this, make sure that python, pip and tgtg are installed!
# In a command line: pip install tgtg>=0.7.0

from tgtg import TgtgClient

# ⚠ Change your email/password combo here.
# If you don't have a password, reset it from the app.
email = "Your TGTG mail"
password = "Your TGTG password"

# Set up a tgtg client
client = TgtgClient(email=email, password=password)

# Necessary to actually get the tokens
client.get_items()

# Print the result!
print("Copy paste this in your configuration.yaml file:")
print("")
print("sensor:")
print("  - platform: tgtg")
print("    username: '" + email + "'")
print("    password: '" + password + "'")
print("    access_token: '" + client.access_token + "'")
print("    refresh_token: '" + client.refresh_token + "'")
print("    user_id: '" + client.user_id + "'")
print("    scan_interval: 900")
print("")
input("Press enter to quit ...")