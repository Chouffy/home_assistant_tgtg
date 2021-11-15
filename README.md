# TooGoodToGo items stock as a sensor in Home Assistant

This aim to show the stock of one or multiple [TooGoodToGo](https://toogoodtogo.com/) item using the [tgtg-python](https://github.com/ahivert/tgtg-python) library.

## Usage

### Installation via [HACS](https://hacs.xyz/)

1. Search for *TooGoodToGo* in the Integration tab of HACS
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

      # Optional, for token-based authentication
      access_token: "abc123"
      refresh_token: "abc123"
      user_id: "123"
    ```

    * If your account doesn't have a password, try to reset your password from the app.
    * I suggest `scan_interval: 900` to refresh the stock every 15 minutes
    * To avoid email, specify `access_token`, `refresh_token` and `user_id`. They can be retrieved using [this example](https://github.com/ahivert/tgtg-python#retrieve-tokens-to-avoid-login-email)

1. Restart the Home Assistant server

### How to get the item_id

Check the [tgtg_get_favorites_item_id](./tgtg_get_favorites_item_id.py) script!

1. Set up email and password
1. Run it
1. Copy the full output in the `configuration.yaml` for the `item` section

## Features

Actual:

* Fetch each item stock defined
* Authenticate using email/password or tokens

Maybe one day:

* Retrieve all favorites instead of a manual list of item_id, but this would mean using your "true" TGTG account ...
* Parse additional available information from the `tgtg` API to Home-Assistant Attributes
