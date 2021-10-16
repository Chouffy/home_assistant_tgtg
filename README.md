# TooGoodToGo items stock as a sensor in Home Assistant

This aim to show the stock of one or multiple [TooGoodToGo](https://toogoodtogo.com/) item using the [tgtg-python](https://github.com/ahivert/tgtg-python) library.

## Usage

1. Add this repository `https://github.com/Chouffy/home_assistant_tgtg` as a custom repository with *integration* type
1. Click *Install*
1. Add the following in your `/config/configuration.yaml`:

    ```yaml
    sensor:
    - platform: tgtg
      username: 'Your TGTG mail'
      password: 'Your TGTG password'
      scan_interval: 900
      item:
        # item_id 1
        - 1234
        # item_id 2
        - 5678
    ```

    * I suggest `scan_interval: 900` to refresh the stock every 15 minutes

1. Restart the Home Assistant server

### How to get the item_id

Check the [tgtg_get_favorites_item_id](./tgtg_get_favorites_item_id.py) script!

1. Set up email and password
1. Run it
1. Copy the full output in the `configuration.yaml` for the `item` section

## Features

Actual:

* Fetch each item stock defined

Maybe one day:

* Retrieve all favorites instead of a manual list of item_id
  * But this would mean using your "true" TGTG account which could be blocked due to non authorized API access ...
