# Too Good To Go items stock as a sensor in Home Assistant

This aim to show the stock of one or multiple [Too Good To Go](https://toogoodtogo.com/) item using the [tgtg-python](https://github.com/ahivert/tgtg-python) library.\
Sensor data can be used afterward to generate notifications, history graphs, ... share your best examples in the [Discussion tab](https://github.com/Chouffy/home_assistant_tgtg/discussions)!

## Features

- Fetch each item stock defined
- Authenticate using tokens
- Retrieve all favorites instead of a manual list of item_id if no `item:` are defined
- Retrieve additional information as attributes, if available:
  - Item ID
  - Price and original value
  - Pick-up start and end time
  - Sold-out time
  - Orders placed (if above 0, then below attributes also appear)
    - Total quantity ordered (total from 1 or more orders placed)
    - Pickup window changed (true/false)
    - Cancel-until time
- [Dashboard card example
](https://github.com/Chouffy/home_assistant_tgtg?tab=readme-ov-file#dashboard-card-example)
## Installation

1. Search for _TooGoodToGo_ in the Integration tab of HACS
1. Click _Install_
1. Restart Home Assistant
   - ⚠ Each time you add/remove a favorite in the TGTG app, **reload the integration**. Favorites are only updated while the integration is initialzing!

## Configuration is performed in the UI!

### How to get item_id

TBC

## Dashboard card example

Here is an example for a card on your Home Assistant dashboard created by @wallieboy, updated by @Sarnog in https://github.com/Chouffy/home_assistant_tgtg/issues/73 and @tjorim. Support for images was later added by @ov3rk1ll in https://github.com/Chouffy/home_assistant_tgtg/pull/139.\
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
