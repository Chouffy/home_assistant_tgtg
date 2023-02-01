#!/usr/bin/python3

# Before running this, make sure that python3, pip and tgtg are installed!
# In a command line: pip install tgtg>=0.10.0

from tgtg_get_tokens import tgtgClient

# The same client is re-used from the 1st script, so no need to rebuild it again

# Below is if you want to get only one item_id information
# tgtgReply = client.get_item(item_id=529241)

# Get all favorites
tgtgReply = tgtgClient.get_items()

# Print them in a Home Assistant friendly way
print("")
print("Copy-paste this in your configuration.yaml file, inside the sensor / tgtg section:")
print("")
print('  item:')
for item in tgtgReply:
    print('    #', item['display_name'])
    print('    - ', item['item']['item_id'])

print("")
input("Press enter to quit ...")