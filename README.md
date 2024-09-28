# DataFactory scraper

Library for scraping football data from [DataFactory](https://www.datafactory.la/) matches and other websites that this company provides.

## Installation

To install this library, use:

```bash
pip install datafactoryfc
```

To upgrade the library, use:

```bash
pip install --upgrade datafactoryfc
```

## About

The library has a main function, which is used to retrieve the data of a match, and several other functions to process that information and return specific events.

```python
import datafactoryfc as dfc

data = dfc.get_data('copalpf', 2643544)
```

This function retrieves the match information in JSON format. We can then process that data with the help of other functions:

```python
dfc.get_passes(data)
dfc.get_shots(data)
dfc.get_corners(data)
```

Alternatively, we can provide the league name and match ID directly to these functions in a list format. Always put the league name first and the match ID second:

```python
dfc.get_passes(['copalpf', 2643544])
dfc.get_fouls(['copalpf', 2643544])
dfc.get_throwins(['copalpf', 2643544])
```