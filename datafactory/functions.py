import pandas as pd
import numpy as np
import requests

def process_coordinates(df, hasEnd=True):
    df['x'] = df['coord'].apply(lambda x: x['1']['x'])
    df['y'] = df['coord'].apply(lambda x: x['1']['y'])
    
    if hasEnd:
        df['endX'] = df['coord'].apply(lambda x: x['2']['x'])
        df['endY'] = df['coord'].apply(lambda x: x['2']['y'])
        
        df['endX'] = (df['endX'] + 1) * 50
        df['endY'] = (df['endY'] + 1) * 50

    df['x'] = (df['x'] + 1) * 50
    df['y'] = (df['y'] + 1) * 50
    
    if hasEnd:
        df.loc[df['t'].apply(lambda x: x['half']) == 2, ['x', 'y', 'endX', 'endY']] = 100 - df.loc[df['t'].apply(lambda x: x['half']) == 2, ['x', 'y', 'endX', 'endY']]
    else:
        df.loc[df['t'].apply(lambda x: x['half']) == 2, ['x', 'y']] = 100 - df.loc[df['t'].apply(lambda x: x['half']) == 2, ['x', 'y']]
    
    df['y'] = 100 - df['y']
    if hasEnd:
        df['endY'] = 100 - df['endY']

    df.drop('coord', axis=1, inplace=True)
    return df

def process_time(df):
    df['minute'] = df.apply(lambda row: row['t']['m'] if row['t']['half'] == 1 else row['t']['m'], axis=1)
    df['seconds'] = df.apply(lambda row: row['t']['s'], axis=1)
    df.drop('t', axis=1, inplace=True)
    return df

def get_player_name(player_id, data):
    if pd.isna(player_id):
        return None
    player_id = int(player_id)
    return data['players'].get(f'{player_id}', {}).get('name', {}).get('shortName', None)

def get_request(league, match_id):
    """Obtiene la respuesta de un partido.

    Args:
        league (str): Nombre de la liga.
        match_id (int): Id del partido.

    Returns:
        response: JSON con la respuesta.
    """
    response = requests.get(f'https://gamecenter.clarin.com/v3/htmlCenter/data/deportes/futbol/{league}/events/{match_id}.json')
    return response.json()

def get_match_passes(data, all_passes=True):
    passes = data['incidences']['correctPasses']
    df = pd.DataFrame.from_dict(passes, orient='index')

    if all_passes:
        incorrect_passes = data['incidences']['incorrectPasses']
        df_incorrect = pd.DataFrame.from_dict(incorrect_passes, orient='index')
        df = pd.concat([df, df_incorrect])

    df = process_coordinates(df)
    df = process_time(df)

    df['playerName'] = df['plyrId'].apply(lambda x: get_player_name(x, data))
    df['reciverName'] = df['recvId'].apply(lambda x: get_player_name(x, data))

    df['beggining'] = np.sqrt(np.square(100 - df['x']) + np.square(50 - df['y']))
    df['end'] = np.sqrt(np.square(100 - df['endX']) + np.square(50 - df['endY']))
    df['isProgressive'] = df.apply(lambda row: row['end'] / row['beggining'] < 0.75, axis=1)

    df = df.rename(columns={
        'team': 'teamId',
        'plyrId': 'playerId',
        'recvId': 'reciverId'
    })

    df = df[['teamId', 'minute', 'seconds', 'playerId', 'playerName', 'reciverId', 'reciverName', 'x', 'y', 'endX', 'endY', 'isProgressive']]
    df = df.reset_index(drop=True)

    return df

def get_shotmap(data):
    shots = data['incidences']['shots']
    df = pd.DataFrame.from_dict(shots, orient='index')

    df = process_coordinates(df)
    df = process_time(df)

    df['playerName'] = df['plyrId'].apply(lambda x: get_player_name(x, data))
    df['assistName'] = df['assBy'].apply(lambda x: get_player_name(x, data))
    df['catchName'] = df['ctchBy'].apply(lambda x: get_player_name(x, data))

    conditions = [
        df['type'].isin([9, 11, 13]),
        df['type'] == 33,
    ]
    values = ['Gol', 'Al arco']
    df['outcome'] = np.select(conditions, values, default='Tiro')

    df = df.rename(columns={
        'team': 'teamId',
        'plyrId': 'playerId',
        'assBy': 'assistId',
        'ctchBy': 'catchId'
    })

    df = df[['teamId', 'minute', 'seconds', 'playerId', 'playerName', 'x', 'y', 'endX', 'endY', 'outcome', 'assistId', 'assistName', 'catchId', 'catchName']]
    df = df.reset_index(drop=True)

    return df

def get_fouls_map(data):
    fouls = data['incidences']['fouls']
    df = pd.DataFrame.from_dict(fouls, orient='index')

    df = process_coordinates(df, hasEnd=False)
    df = process_time(df)

    df['fouledName'] = df['recvId'].apply(lambda x: get_player_name(x, data))
    df['playerName'] = df['plyrId'].apply(lambda x: get_player_name(x, data))

    df = df.rename(columns={
        'team': 'teamId',
        'plyrId': 'playerId',
        'recvId': 'fouledId'
    })

    df = df[['teamId', 'minute', 'seconds', 'playerId', 'playerName', 'fouledId', 'fouledName', 'x', 'y']]
    df = df.reset_index(drop=True)

    return df
