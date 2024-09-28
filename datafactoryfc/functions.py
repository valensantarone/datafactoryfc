import importlib.resources as pkg_resources
import pandas as pd
import numpy as np
import requests
import json
from .exceptions import MatchDoesntHaveInfo, InvalidMatchInput
from datafactoryfc import assets

def _match_input_validation(match_input):
    if isinstance(match_input, list):
        if len(match_input) == 2 and isinstance(match_input[0], str) and isinstance(match_input[1], int):
            league, match_id = match_input
            data = get_data(league, match_id)
        else:
            raise InvalidMatchInput
    elif isinstance(match_input, dict):
        data = match_input
    else:
        raise InvalidMatchInput

    return data

def _process_coordinates(df, has_end=True):
    """Process the coordinates (x, y) and optionally the end coordinates (endX, endY)."""
    
    df['x'] = df['coord'].apply(lambda c: c['1']['x'])
    df['y'] = df['coord'].apply(lambda c: c['1']['y'])

    if has_end:
        df['endX'] = df['coord'].apply(lambda c: c['2']['x'])
        df['endY'] = df['coord'].apply(lambda c: c['2']['y'])
        df[['endX', 'endY']] = (df[['endX', 'endY']] + 1) * 50
    
    df[['x', 'y']] = (df[['x', 'y']] + 1) * 50
    
    half_2_mask = df['t'].apply(lambda x: x['half']) == 2
    if has_end:
        df.loc[half_2_mask, ['x', 'y', 'endX', 'endY']] = 100 - df.loc[half_2_mask, ['x', 'y', 'endX', 'endY']]
    else:
        df.loc[half_2_mask, ['x', 'y']] = 100 - df.loc[half_2_mask, ['x', 'y']]

    df['y'] = 100 - df['y']
    if has_end:
        df['endY'] = 100 - df['endY']

    df.drop('coord', axis=1, inplace=True)
    return df

def _process_time(df):
    """Process time into minutes and seconds and sort events chronologically."""
    
    df['minute'] = df['t'].apply(lambda t: t['m'])
    df['seconds'] = df['t'].apply(lambda t: t['s'])
    
    df.drop('t', axis=1, inplace=True)
    df = df.sort_values(by=['minute', 'seconds']).reset_index(drop=True)
    return df

def _get_player_name(player_id, data):
    """Return player short name by player_id."""
    
    if pd.isna(player_id):
        return None
    player_id = int(player_id)
    return data['players'].get(str(player_id), {}).get('name', {}).get('shortName')

def _get_team_name(team_id, data):
    """Return team name based on team_id."""
    
    if team_id == data['match']['homeTeamId']:
        return data['match']['homeTeamName']
    elif team_id == data['match']['awayTeamId']:
        return data['match']['awayTeamName']
    return None

def get_data(league, match_id):
    """Fetch match data from API in JSON format.
    
    Args:
        league (str): League name found in the URL.
        match_id (int): Match ID found in the URL.

    Returns:
        dict: JSON response with match data.
    """
    
    url = f'https://gamecenter.clarin.com/v3/htmlCenter/data/deportes/futbol/{league}/events/{match_id}.json'
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def get_passes(match_input, all_passes=True, with_xT=True):
    """Retrieve passes from the match (both correct and incorrect).
    
    Args:
        match_input (list or dict): Either the match data (JSON) or list with league and match_id.
        all_passes (bool): If True, return both correct and incorrect passes.
        with_xT (bool): If True, return xT value for each pass.

    Returns:
        pd.DataFrame: DataFrame with all pass information.
    """
    
    data = _match_input_validation(match_input)
    
    passes = data['incidences'].get('correctPasses', {})
    if not passes:
        raise MatchDoesntHaveInfo

    df = pd.DataFrame.from_dict(passes, orient='index')

    if all_passes:
        incorrect_passes = data['incidences'].get('incorrectPasses', {})
        df_incorrect = pd.DataFrame.from_dict(incorrect_passes, orient='index')
        df = pd.concat([df, df_incorrect])

    df = _process_coordinates(df)
    df = _process_time(df)

    df['playerName'] = df['plyrId'].apply(lambda x: _get_player_name(x, data))
    df['receiverName'] = df['recvId'].apply(lambda x: _get_player_name(x, data))

    df['beginning'] = np.hypot(100 - df['x'], 50 - df['y'])
    df['end'] = np.hypot(100 - df['endX'], 50 - df['endY'])
    df['isProgressive'] = np.where((df['end'] / df['beginning'] < 0.75) & (df['recvId'].notna()), True, False)

    df.rename(columns={'team': 'teamId', 'plyrId': 'playerId', 'recvId': 'receiverId'}, inplace=True)
    df['teamName'] = df['teamId'].apply(lambda team_id: _get_team_name(team_id, data))

    df = df[['teamId', 'teamName', 'minute', 'seconds', 'playerId', 'playerName', 'receiverId', 'receiverName', 'x', 'y', 'endX', 'endY', 'isProgressive']]
    
    if with_xT:
        df = xT(df)
        
    return df

def get_shots(match_input):
    """Retrieve shot data from the match.
    
    Args:
        match_input (list or dict): Either match data (JSON) or list with league and match_id.

    Returns:
        pd.DataFrame: DataFrame with shot information.
    """
    
    data = _match_input_validation(match_input)

    shots = data['incidences']['shots']
    df = pd.DataFrame.from_dict(shots, orient='index')

    df = _process_coordinates(df)
    df = _process_time(df)

    df['playerName'] = df['plyrId'].apply(lambda x: _get_player_name(x, data))
    
    if 'assBy' in df.columns:
        df['assistName'] = df['assBy'].apply(lambda x: _get_player_name(x, data))
    else:
        df['assistId'] = None
        df['assistName'] = None
        
    if 'ctchBy' in df.columns:
        df['catchName'] = df['ctchBy'].apply(lambda x: _get_player_name(x, data))
    else:
        df['catchId'] = None
        df['catchName'] = None

    conditions = [df['type'].isin(range(9, 14)), df['type'] == 33]
    outcomes = ['Goal', 'On Target']
    df['outcome'] = np.select(conditions, outcomes, default='Missed')

    df.rename(columns={'team': 'teamId', 'plyrId': 'playerId', 'assBy': 'assistId', 'ctchBy': 'catchId'}, inplace=True)
    df['teamName'] = df['teamId'].apply(lambda team_id: _get_team_name(team_id, data))

    df = df[['teamId', 'teamName', 'minute', 'seconds', 'playerId', 'playerName', 'x', 'y', 'endX', 'endY', 'outcome', 'assistId', 'assistName', 'catchId', 'catchName']]
    return df

def get_fouls(match_input):
    """Retrieve fouls from the match.
    
    Args:
        match_input (list or dict): Either match data (JSON) or list with league and match_id.

    Returns:
        pd.DataFrame: DataFrame with foul information.
    """
    
    data = _match_input_validation(match_input)

    fouls = data['incidences']['fouls']
    df = pd.DataFrame.from_dict(fouls, orient='index')

    df = _process_coordinates(df, has_end=False)
    df = _process_time(df)

    df['playerName'] = df['plyrId'].apply(lambda x: _get_player_name(x, data))
    df['fouledName'] = df['recvId'].apply(lambda x: _get_player_name(x, data))

    df.rename(columns={'team': 'teamId', 'plyrId': 'playerId', 'recvId': 'fouledId'}, inplace=True)
    df['teamName'] = df['teamId'].apply(lambda team_id: _get_team_name(team_id, data))

    df = df[['teamId', 'teamName', 'minute', 'seconds', 'playerId', 'playerName', 'fouledId', 'fouledName', 'x', 'y']]
    return df


def get_throwins(match_input, with_xT=True):
    """Retrieve all throw-ins from both teams of a match.
    
    Args:
        match_input (list or dict): Either match data (JSON) or list with league and match_id.
        with_xT (bool): If True, return xT value for each pass.

    Returns:
        pd.DataFrame: DataFrame with throw-in information.
    """
    
    data = _match_input_validation(match_input)

    throwin = data['incidences']['throwIn']
    df = pd.DataFrame.from_dict(throwin, orient='index')
    
    df = _process_coordinates(df)
    df = _process_time(df)
    
    df['playerName'] = df['plyrId'].apply(lambda x: _get_player_name(x, data))
    
    df = df.rename(columns={
        'team': 'teamId',
        'plyrId': 'playerId'
    })
    
    df['teamName'] = df['teamId'].apply(lambda team_id: _get_team_name(team_id, data))

    df = df[['teamId', 'teamName', 'minute', 'seconds', 'playerId', 'playerName', 'x', 'y', 'endX', 'endY']]
    df = df.reset_index(drop=True)
    
    if with_xT:
        df = xT(df)
    
    return df

def get_corners(match_input, with_xT=True):
    """Retrieve all corner kicks from both teams of a match.
    
    Args:
        match_input (list or dict): Either match data (JSON) or list with league and match_id.
        with_xT (bool): If True, return xT value for each pass.

    Returns:
        pd.DataFrame: DataFrame with corner kick information.
    """
    
    data = _match_input_validation(match_input)
    
    corners = data['incidences']['cornerKicks']
    df = pd.DataFrame.from_dict(corners, orient='index')

    df = _process_coordinates(df)
    df = _process_time(df)
    
    df['playerName'] = df['plyrId'].apply(lambda x: _get_player_name(x, data))
    
    df = df.rename(columns={
        'team': 'teamId',
        'plyrId': 'playerId'
    })
    
    df['teamName'] = df['teamId'].apply(lambda team_id: _get_team_name(team_id, data))
    
    df = df[['teamId', 'teamName', 'minute', 'seconds', 'playerId', 'playerName', 'x', 'y', 'endX', 'endY']]
    df = df.reset_index(drop=True)
    
    if with_xT:
        df = xT(df)
    
    return df

def xT(df):
    with pkg_resources.open_text(assets, 'xTGrid.json') as f:
        xT = json.load(f)
    xT = np.array(xT)
    xT_rows, xT_cols = xT.shape
    
    df['x_xT'] = df['x'] * 1.05
    df['y_xT'] = df['y'] * 0.68
    df['endX_xT'] = df['endX'] * 1.05
    df['endY_xT'] = df['endY'] * 0.68
    
    df_xT = df.dropna(subset=['x_xT', 'y_xT', 'endX_xT', 'endY_xT'])

    df_xT['x1_bin'] = pd.cut(df_xT['x_xT'], bins=xT_cols, labels=False)
    df_xT['y1_bin'] = pd.cut(df_xT['y_xT'], bins=xT_rows, labels=False)

    df_xT['x2_bin'] = pd.cut(df_xT['endX_xT'], bins=xT_cols, labels=False)
    df_xT['y2_bin'] = pd.cut(df_xT['endY_xT'], bins=xT_rows, labels=False)

    df_xT['x1_bin'] = df_xT['x1_bin'].astype(int)
    df_xT['y1_bin'] = df_xT['y1_bin'].astype(int)
    df_xT['x2_bin'] = df_xT['x2_bin'].astype(int)
    df_xT['y2_bin'] = df_xT['y2_bin'].astype(int)
    
    df_xT['start_zone_value'] = df_xT.apply(lambda x: xT[x['y1_bin']][x['x1_bin']], axis=1)
    df_xT['end_zone_value'] = df_xT.apply(lambda x: xT[x['y2_bin']][x['x2_bin']], axis=1)
    
    df_xT['xT'] = df_xT['end_zone_value'] - df_xT['start_zone_value']
    
    if 'receiverId' in df_xT.columns:
        df_xT['xT'] = np.where(pd.isna(df_xT['receiverId']), 0, df_xT['xT'])
    
    df_xT = df_xT.drop(columns=['x1_bin', 'y1_bin', 'x2_bin', 'y2_bin', 'start_zone_value', 'end_zone_value', 'x_xT', 'y_xT', 'endX_xT', 'endY_xT'])
    
    return df_xT
