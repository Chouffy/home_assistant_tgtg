# TooGoodToGo items stock as a sensor in Home Assistant



This aim to show the stock of one or multiple [TooGoodToGo](https://toogoodtogo.com/) item using the [tgtg-python](https://github.com/ahivert/tgtg-python) library.  
Sensor data can be used afterward to generate notifications, history graphs, ... share your best examples in the [Discussion tab](https://github.com/Chouffy/home_assistant_tgtg/discussions)!

## Usage

### Installation via [HACS](https://hacs.xyz/)

1. Search for *TooGoodToGo* in the Integration tab of HACS
1. Click *Install*
1. Install required packages on your local PC:
    * [Python >=3.8](https://www.python.org/downloads/)
    * [tgtg-python](https://github.com/ahivert/tgtg-python) library: In a command line, type `pip install tgtg` or `pip install --upgrade tgtg` if you already have it.
1. Run the [tgtg_get_tokens](./tgtg_get_tokens.py) script on your local PC:
1. Paste the result in your `/config/configuration.yaml`.
1. Restart the Home Assistant server
    * ⚠ Each time you add/remove a favorite in the TGTG app, **restart your Home Assistant**. Favorites are only updated at boot!

### Configuration option

```yaml
sensor:
- platform: tgtg

  # Mandatory: tokens for authentication - see the tgtg_get_tokens.py script
  access_token: "abc123"
  refresh_token: "abc123"
  user_id: "123"
  cookie: "123"

  # Optional: email so you know which account is used
  username: 'Your TGTG mail'

  # Optional: Refresh the stock every 15 minutes
  scan_interval: 900

  # Optional, use defined items ID instead to get your favorites
  item:
    # item_id 1
    - 1234
    # item_id 2
    - 5678

  # Optional: user agent - by default, the latest one is retrieved from the Google Play store
  #user_agent: "TGTG/22.2.1 Dalvik/2.1.0 (Linux; U; Android 9; SM-G955F Build/PPR1.180610.011)"

```

`access_token`, `refresh_token` and `user_id` can be retrieved using the [tgtg_get_tokens](./tgtg_get_tokens.py) script!

### How to get item_id

Check the [tgtg_get_favorites_item_id](./tgtg_get_favorites_item_id.py) script!

1. Set up email/password
1. Run it
1. Copy the full output in the `configuration.yaml` for the `item` section

## Features

* Fetch each item stock defined
* Authenticate using tokens
* Retrieve all favorites instead of a manual list of item_id if no `item:` are defined
* Retrieve additional information as attributes, if available:
    * Item ID
    * TooGoodToGo price and original value
    * Pick-up start and end
    * Sold-out date

## Q&A

* It was working before, but now all TooGoodToGo sensors are "not available"
   * Try to update your tokens using [the script](https://github.com/Chouffy/home_assistant_tgtg/blob/main/tgtg_get_tokens.py) and restart Home Assistant
* I have a sensor that shows now as unavailable when there's no stock
    * Try add it manually using Item ID - See [this issue](https://github.com/Chouffy/home_assistant_tgtg/issues/18)
* The `tgtg` integration won't start, all my sensors are unavailable and I have a list of manually defined items ID
    * Double-check if all items ID defined manually are correct. The integration [don't support unknown or incorrect item ID - see issue](https://github.com/Chouffy/home_assistant_tgtg/issues/22).
