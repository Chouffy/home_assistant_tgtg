# Too Good To Go integration for Home Assistant

> [!IMPORTANT]
> This integration is currently not functional because of https://github.com/Chouffy/home_assistant_tgtg/issues/187 \
> Unfortunately this is out of our control, keep an eye on the upstream library \
> https://github.com/ahivert/tgtg-python

This aims to show the stock of one or multiple [Too Good To Go](https://toogoodtogo.com/) items using the [tgtg-python](https://github.com/ahivert/tgtg-python) library.
Sensor data can be used afterward to generate notifications, history graphs, ... share your best examples in the [Discussion tab](https://github.com/Chouffy/home_assistant_tgtg/discussions)!

## Features

- **Easy setup** - No tokens, Docker containers, or Python scripts needed! Just enter your email and click the magic link.
- **Config Flow** - Full UI-based configuration
- **Automatic favorites** - Retrieves all your favorites from the TGTG app (with pagination for accounts with 20+ favorites)
- **Smart polling** - More frequent updates (every 3 minutes) during sales windows when items are likely to become available
- **API rate limiting** - Built-in 1 second delays between API calls to prevent rate limiting issues
- **Reauth support** - Handles token expiration gracefully
- **Diagnostics** - Built-in diagnostics support for troubleshooting
- **Custom item IDs** - Optionally add non-favorite items during setup
- **Rich attributes** for each sensor:
  - Item ID and URL
  - Price and original value
  - Pick-up start and end time
  - Sold-out timestamp
  - Store logo and cover image URLs
  - Pickup location (latitude/longitude)
  - Orders placed and quantity ordered
  - Pickup window changed status
  - Cancel-until time

## Installation

### Via [HACS](https://hacs.xyz/) (Recommended)

1. Search for _TooGoodToGo_ in the Integration tab of HACS
2. Click _Install_
3. Restart Home Assistant
4. Go to **Settings** → **Devices & Services** → **Add Integration**
5. Search for "TooGoodToGo" and follow the setup wizard
6. Enter your TGTG email address
7. Check your email and click the magic link **on a PC** (not on mobile if the TGTG app is installed)
8. Optionally add any non-favorite item IDs
9. Done!

## Configuration

Configuration is performed entirely in the UI. No YAML configuration is needed.

### Adding custom item IDs

During setup, you can optionally add item IDs for stores that aren't in your favorites. To find an item ID:

1. Open the Too Good To Go app
2. Navigate to the store you want to add
3. Share the store link - it will look like: `https://share.toogoodtogo.com/item/123456/`
4. The number at the end (`123456`) is the item ID

## How polling works

- **Default polling**: Every 60 minutes
- **Sales window polling**: Every 3 minutes when any item is within its sales window
- **Rate limited**: 1 second delay between API calls to prevent being blocked
- **Adaptive**: If API rate limits are hit, polling is automatically reduced to once per hour

> **Note**: Each time you add/remove a favorite in the TGTG app, **reload the integration** for changes to take effect.

## Automation example

Here's an example automation that sends a notification when a TGTG item becomes available:

```yaml
automation:
  - alias: "TGTG Item Available"
    trigger:
      - platform: state
        entity_id: sensor.tgtg_your_store_name
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state | int > 0 }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "TGTG Surprise Bag Available!"
          message: >
            {{ trigger.to_state.attributes.friendly_name }} has {{ trigger.to_state.state }} bag(s) available!
            Pickup: {{ trigger.to_state.attributes.pickup_start | as_datetime | as_local }}
            Price: {{ trigger.to_state.attributes.item_price }}
          data:
            url: "{{ trigger.to_state.attributes.item_url }}"
```

> **Note**: All attributes use snake_case (underscores), e.g., `pickup_start`, `item_price`, `item_url`.

## Dashboard card example

Here is an example for a card on your Home Assistant dashboard created by @wallieboy, updated by @Sarnog in https://github.com/Chouffy/home_assistant_tgtg/issues/73 and @tjorim. Support for images was later added by @ov3rk1ll in https://github.com/Chouffy/home_assistant_tgtg/pull/139.
Make sure you install the custom `auto-entities` and `multiple-entity-row` cards as well.

```yaml
type: custom:auto-entities
card:
  type: entities
  title: TGTG Surprise Bags
filter:
  template: |-
    {% for state in states.sensor if 'sensor.tgtg_' in state.entity_id %}
      {% set entity_id = state.entity_id %}
      {% set state = states(entity_id) %}
      {%- if is_number(state) and state | int > 0 %}
        {% set pickup_start = state_attr(entity_id, 'pickup_start') %}
        {%- if pickup_start is not none -%}
          {{
            {
              'entity': entity_id,
              'name': state_attr(entity_id, 'friendly_name')[5:],
              'type': "custom:multiple-entity-row",
              'unit': false,
              'secondary_info': as_timestamp(pickup_start) | timestamp_custom('Pickup on %d-%m between %H:%M and ', true) + as_timestamp(state_attr(entity_id, 'pickup_end')) | timestamp_custom('%H:%M, € ', true) + state_attr(entity_id, 'item_price')[:-3],
              'image': state_attr(entity_id, 'logo_url'),
              'tap_action': {
                'action': 'url',
                'url_path': state_attr(entity_id, 'item_url')
              }
            }
          }},
        {%- endif -%}
      {%- endif -%}
    {%- endfor %}
```

![image](https://github.com/Chouffy/home_assistant_tgtg/assets/1294876/db2899ac-0023-4c8b-9f61-07e764408e1f)

## Troubleshooting

### "Additional verification required" during setup

This happens when TGTG's API detects unusual activity. Wait a few hours and try again.

### Integration stops updating

Your tokens may have expired. Go to **Settings** → **Devices & Services**, find the TGTG integration, and use the "Reconfigure" option to reauthenticate.

### Not all favorites showing

If you have more than 20 favorites, make sure you're using version 6.0.0 or later which includes pagination support.

## Breaking changes in v6.0.0

- **New folder structure**: The integration folder has changed from `tgtg/` to `toogoodtogo/`. If upgrading from an older version, you may need to remove the old integration folder manually.
- **Config flow only**: YAML configuration is no longer supported. Migrate to UI-based configuration.
