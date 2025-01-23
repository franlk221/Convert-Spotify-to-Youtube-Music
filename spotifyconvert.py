import os
from dotenv import load_dotenv
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import ytmusicapi
import pickle
load_dotenv('requirements.txt')
# load_dotenv()
YTMUSIC_CLIENT_ID = os.getenv('YTMUSIC_CLIENT_ID')
YTMUSIC_CLIENT_SECRET = os.getenv('YTMUSIC_CLIENT_SECRET')
BREAK_STRINGS = ['0', 'x','finish','done']
EXIT_STRINGS = ['quit', 'exit']

def get_playlists(sp):

    playlists = []

    playlists_query = sp.current_user_playlists()
    while playlists_query:
        for i, playlist in enumerate(playlists_query['items']):
            owner = playlist['owner']['id']
            uri = playlist['uri']
            name = playlist['name']
            desc = playlist['description']
            total = playlist['tracks']['total']
            privacy = 'PUBLIC' if playlists_query['items'][i]['public'] else 'UNLISTED'
            playlists.append({'upload': False, 'uri': uri, 'name': name, 'owner': owner, 'desc': desc, 'privacy': privacy, 'song_queries': [], 'total': total})
        if playlists_query['next']:
            playlists_query = sp.next(playlists_query)
        else:
            playlists_query = None

    return playlists

def print_playlists(titles, playlists):
    for i, playlist in enumerate(playlists):
        include = ' '
        if playlist['name'] in titles:
            include = '!'
        #want to enable override 
        if playlist['upload']:
            include = '*'
        print("[%s] %4d %s | %s | %5d songs" % (include, i + 1, playlist['name'], playlist['owner'], playlist['total']))

def conflict_check(titles, playlists):
    for playlist in playlists:
        if playlist['name'] in titles:
            index = titles.index(playlist['name'])
            print(f'!---Potential Conflict at {index}: Playlist in Spotify and Youtube both called {playlist["name"]}---!')

def get_yt_playlists(ytmusic):

    user_playlists = ytmusic.get_library_playlists(limit=None)
    titles = []
    for playlist in user_playlists:
        titles.append(playlist['title'])
    return titles

def get_spotify_playlist_songs(sp, playlists):

    for playlist in playlists:
        if not playlist['upload']:
            continue

        playlist_query = sp.playlist_items(playlist['uri'])

        while playlist_query:
            for i, song in enumerate(playlist_query['items']):
                artists = ''
                for artist in song['track']['artists']:
                    artists += artist['name'] + ' '
                query = f'{artists} {song['track']['name']}'
                playlist['song_queries'].append(query)
            if playlist_query['next']:
                playlist_query = sp.next(playlist_query)
            else:
                playlist_query = None

    return playlists

def create_yt_playlists(ytmusic, playlists):
    for playlist in playlists:
        if not playlist['upload']:
            continue
        song_queries = playlist['song_queries']
        song_ids = []
        for query in song_queries:
            try:
                search_results = ytmusic.search(query, filter='songs')
                song_ids.append(search_results[0]['videoId'])
            except IndexError:
                print(f'Nothing found for {query}')

        #found that playlists with thousands of songs will somehow lose songs if all added at same time
        # chunking to prevent 
        n = 500
        chunk_song_ids = [song_ids[i:i + n] for i in range(0, len(song_ids), n)] 
        try:
            playlist_id = ytmusic.create_playlist(playlist['name'], playlist['desc'], playlist['privacy'], chunk_song_ids[0], None)
            for chunk in chunk_song_ids[1:]:
                ytmusic.add_playlist_items(playlist_id, chunk, None, True)
        except:
            print('Error in creating playlist')
            # might need to renew ytmusic if search takes too long
            # save data for playlist TODO: implement loading from pickle file 
            with open(f'saved_{playlist['uri']}_dict.pkl', 'wb') as f:
                pickle.dump(playlist, f)

            with open(f'saved_{playlist['uri']}_song_ids.pkl', 'wb') as f:
                pickle.dump(song_ids, f)

def load_pickle():
    #TODO
    # with open('saved_All weekly_dict.pkl', 'rb') as f:
    #     playlist = pickle.load(f)
    # # print(type(playlist), playlist)
    # # print(playlist['name'], playlist['desc'], playlist['privacy'])
    # with open('saved_All weekly_song_ids.pkl', 'rb') as f:
    #     song_ids = pickle.load(f)
    # print(type(song_ids[:10]), song_ids[:10])
    # n = 500
    # chunk_song_ids = [song_ids[i:i + n] for i in range(0, len(song_ids), n)] 
    # print(len(x))
    # ytmusic.create_playlist(playlist['name'], playlist['desc'], playlist['privacy'], song_ids[:50], None)
    # ytmusic.add_playlist_items(playlist_id, song_ids[500:1000], None, True)
    return

def print_help_message():

    print('Boxes marked with a * are selected, a ! means there is same-named playlist in both youtube and spotify (playlist can still be selected)')
    print('Enter "all" to select every playlist \n enter in a number or range of numbers to select specific playlists eg "3" or "1,3,7,8" or "1-5", "7-9" \
            \n enter "reset" to unselect everything')
    print(f'Enter {BREAK_STRINGS} to finish selection and begin transfer')
    print(f'Enter "show" to see what is selected so far \nTo quit enter {EXIT_STRINGS}')

def user_input_handler(titles, playlists):

    print_help_message()
    while True:
        response = input().lower().strip()
        if response in EXIT_STRINGS:
            quit()
        elif response in BREAK_STRINGS:
            break
        elif response == 'help': 
            print_help_message()
        elif response == 'all':
            for playlist in playlists:
                playlist['upload'] = True
            print('All Playlists Selected')
        elif response == 'reset':
            for playlist in playlists:
                playlist['upload'] = False
            print('All Playlists Unselected')
        elif response == 'show':
            print_playlists(titles, playlists)
        elif response == 'conflict':
            conflict_check(titles, playlists)
        
        else:
            nums = proc_input(response)
            for num in nums:
                playlists[num - 1]['upload'] = True


    return playlists

def proc_input(input):

    selections = []
    strings = input.split(',')
    for s in strings:
        try:
            if '-' in s:
                ranges = s.split('-')
                start, end = map(int, ranges)
                selections.extend(range(start, end + 1))
            else:  
                selections.append(int(s))
        except:
            print(f'input {s} not recognised')

    return selections

        
def main():

    scope = "user-library-read playlist-modify-public playlist-read-private playlist-modify-private"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    ytmusic = ytmusicapi.YTMusic("oauth.json", oauth_credentials=ytmusicapi.auth.oauth.OAuthCredentials(client_id=YTMUSIC_CLIENT_ID, client_secret=YTMUSIC_CLIENT_SECRET))
    
    titles = get_yt_playlists(ytmusic)
    playlists = get_playlists(sp)
    print_playlists(titles, playlists)
    #filter playlists 
    user_input_handler(titles, playlists)
    print('Starting transfer')
    start = time.time()
    playlists = get_spotify_playlist_songs(sp, playlists)
    # TODO: add a review before creation
    create_yt_playlists(ytmusic, playlists)

    end = time.time()
    print(f'Transfer complete in {end - start} seconds')
    # search_results = ytmusic.search("Odetta god on our side")
    # print(search_results[0]['videoId'])
    # ytmusic.create_playlist('Tester','test desc', "PRIVATE", ['tU2Wtddi27s'], None)


if __name__ == '__main__':
    main()