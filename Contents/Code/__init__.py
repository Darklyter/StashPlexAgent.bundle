import os, urllib, urllib2, json
import dateutil.parser as dateparser
#from Helpers import *
import copy

# preferences
preference = Prefs
DEBUG = preference['debug']
if DEBUG:
  Log('Agent debug logging is enabled!')
else:
  Log('Agent debug logging is disabled!')

def ValidatePrefs():
    pass

def Start():
    Log("Stash metadata agent started")
    HTTP.Headers['Accept'] = 'application/json'
    HTTP.CacheTime = 0.1
    ValidatePrefs()

def HttpReq(url, authenticate=True, retry=True):
    if DEBUG:
        Log("Requesting: %s" % url)
    api_string = ''
    if Prefs['APIKey']:
        api_string = '&apikey=%s' % Prefs['APIKey']

    if Prefs['UseHTTPS']:
        connectstring = 'https://%s:%s/graphql?query=%s%s'
    else:
        connectstring = 'http://%s:%s/graphql?query=%s%s'
    try:
        connecttoken = connectstring % (Prefs['Hostname'].strip(), Prefs['Port'].strip(), url, api_string)
        if DEBUG:
            Log(connecttoken)
        return JSON.ObjectFromString(
            HTTP.Request(connecttoken).content)
    except Exception as e:
        if not retry:
            raise e
        return HttpReq(url, authenticate, False)

# set title with stash metadata
# TODO: add advanced mode to be able to format title with any scene metadata
def FormattedTitle(data, fallback_title=None):
    title = data['title']
    title_format = Prefs['TitleFormat']

    def remove_prefix(text, prefix):
        if text.startswith(prefix):
            return text[len(prefix):]
        return text  # or whatever

    if title is None or title == u'':
        Log("Stash title is empty, using fallback title: %s" % fallback_title)
        return fallback_title
    else:
        performer = ""
        studio = ""
        date = data['date']
        title = data['title']
        if "performer" in title_format:
            performers = copy.copy(data['performers'])
            Log("original performers: %s" % performers)
            if len(performers) > 0:
                # filter out performers with no name or performers with the tag 'PlexPluginSkipTitle'
                for idx in range(len(performers)-1):
                    performer = performers[idx]
                    Log("check performer: %s" % performer['name'])
                    if 'name' in performer and performer['name'] is None or performer['name'] == u'':
                        performers.remove(performer)
                    if 'tags' in performer and performer['tags'] is not None and len(performer['tags']) > 0:
                        if Prefs["IgnoreTags"]:
                            ignore_tags = Prefs["IgnoreTags"].split(",")
                            ignore_tags = list(map(lambda x: x.strip(), ignore_tags))
                        else:
                            ignore_tags = []
                        for tag in performer['tags']:
                            if tag['id'] in ignore_tags:
                                performers.remove(performer)
                                continue
                Log("filtered performers: %s" % performers)
                if (len(performers) > 0 and performers[0]['name']):
                    performer = performers[0]['name']
                    # remove duplicate performer name from title
                    title = remove_prefix(title, performer)
                    title = remove_prefix(title, " - ")
                    title = title.strip()
        if "studio" in title_format:
            studio = data['studio']['name']

        title = title_format.format(
            performer=performer,
            title=title,
            date=data['date'],
            studio=studio
        )
    return title


class StashPlexAgent(Agent.Movies):
    name = 'Stash Plex Agent'
    languages = [Locale.Language.English]
    primary_provider = True
    fallback_agent = False
    contributes_to = None
    accepts_from = ['com.plexapp.agents.xbmcnfo', 'com.plexapp.agents.phoenixadult', 'com.plexapp.agents.data18-phoenix', 'com.plexapp.agents.adultdvdempire']

    def search(self, results, media, lang):
        DEBUG = Prefs['debug']
        mediaFile = media.items[0].parts[0].file
        filename = String.Unquote(mediaFile).encode('utf8', 'ignore')
        filename_clean = os.path.splitext(os.path.basename(filename))[0]
        if (Prefs["UseFullMediaPath"]):
            file_query = r"""query{findScenes(scene_filter:{path:{value:"<FILENAME>",modifier:EQUALS}}){scenes{id,title,date,studio{id,name}}}}"""
        else:
            file_query = r"""query{findScenes(scene_filter:{path:{value:"\"<FILENAME>\"",modifier:INCLUDES}}){scenes{id,title,date,studio{id,name}}}}"""
            filename = os.path.splitext(os.path.basename(filename))[0]
        if filename:
            filename = str(urllib2.quote(filename.encode('UTF-8')))
            query = file_query.replace("<FILENAME>", filename)
            request = HttpReq(query)
            if DEBUG:
                Log(request)
            movie_data = request['data']['findScenes']['scenes']
            score = 100 if len(movie_data) == 1 else 85
            for scene in movie_data:
                if scene['date']:
                    title = scene['title'] + ' - ' + scene['date']
                else:
                    title = filename_clean
                Log("Title Found: " + title + " Score: " + str(score) + " ID:" + scene['id'])
                if Prefs['UseFormattedTitle']:
                    title = FormattedTitle(scene, title)
                results.Append(MetadataSearchResult(id = str(scene['id']), name = title, score = int(score), lang = lang))


    def update(self, metadata, media, lang, force=False):
        DEBUG = Prefs['debug']
        Log("update(%s)" % metadata.id)
        mid = metadata.id
        id_query = "query{findScene(id:%s){path,id,title,details,url,date,rating,rating100,paths{screenshot,stream}movies{movie{id,name}}studio{id,name,image_path,parent_studio{id,name,details}}organized,stash_ids{stash_id}tags{id,name}performers{name,image_path,tags{id,name}}movies{movie{name}}galleries{id,title,url,images{id,title,path,file{size,width,height}}}}}"
        data = HttpReq(id_query % mid)
        data = data['data']['findScene']
        metadata.collections.clear()

        allow_scrape = False
        if (Prefs["RequireOrganized"] and data["organized"]) or not Prefs["RequireOrganized"]:
            if DEBUG and Prefs["RequireOrganized"]:
                Log("Passed 'Organized' Check, continuing...")
            if (Prefs["RequireURL"] and data["url"]) or not Prefs["RequireURL"]:
                if DEBUG and Prefs["RequireURL"]:
                    Log("Passed 'RequireURL' Check, continuing...")
                if (Prefs["RequireStashID"] and len(data["stash_ids"])) or not Prefs["RequireStashID"]:
                    if DEBUG and Prefs["RequireStashID"]:
                        Log("Passed 'RequireURL' Check, continuing...")
                    allow_scrape = True
                else:
                    Log("Failed 'RequireStashID' Check, stopping.")
                    allow_scrape = False
            else:
                Log("Failed 'RequireURL' Check, stopping.")
                allow_scrape = False
        else:
            Log("Failed 'Organized' Check, stopping.")
            allow_scrape = False

        if (Prefs["AddOrganizedCollectionTag"] and data["organized"]):
            Log("Scene marked as organized, adding collection.")
            if (Prefs["OrganizedCollectionTagName"]):
                organized_string = Prefs["OrganizedCollectionTagName"]
            else:
                organized_string = "Organized"
            try:
                metadata.collections.add(organized_string)
            except:
                pass

        if allow_scrape:
            if data['date']:
                try:
                    Log("Trying to parse:" + data["date"])
                    date=dateparser().parse(data["date"])
                except Exception as ex:
                    Log(ex)
                    date=None
                    pass
                # Set the date and year if found.
                if date is not None:
                    metadata.originally_available_at = date
                    metadata.year = date.year

            # Get the title
            if data['title']:
                title = data["title"]
                if Prefs['UseFormattedTitle']:
                    title = FormattedTitle(data, title)
                metadata.title = title

            # Get the Studio
            if not data["studio"] is None:
                metadata.studio = data["studio"]["name"]

            # Get the rating
            if not data["rating"] is None:
                stashRating = float(data["rating100"] / 10)
                metadata.rating = stashRating
                if Prefs["CreateRatingTags"]:
                    if int(data["rating"]) > 0:
                        rating = str(int(data["rating"]))
                        ratingstring = "Rating: " + rating + " Stars"
                        try:
                            metadata.collections.add(ratingstring)
                        except:
                            pass
                if Prefs["SaveUserRatings"]:
                    # set stash rating to plex rating
                    if not stashRating is None:
                        Log('Set media rating to %s' % stashRating)
                        host = "http://127.0.0.1:32400"
                        token = os.environ['PLEXTOKEN']

                        # get section details
                        # inspired by https://github.com/suparngp/plex-personal-shows-agent.bundle/blob/master/Contents/Code/__init__.py#L31
                        sectionQueryEncoded = urllib.urlencode({
                            "X-Plex-Token": token
                        })
                        section_lookup_url = '{host}/library/metadata/{media_id}?{sectionQueryEncoded}'.format(
                            host=host,
                            media_id=media.id,
                            sectionQueryEncoded=sectionQueryEncoded
                        )
                        if DEBUG:
                            Log('Section lookup request: %s' % section_lookup_url)
                        metadata = json.loads(HTTP.Request(url=section_lookup_url, immediate=True, headers={'Accept': 'application/json'}).content)
                        
                        identifier = metadata['MediaContainer']['identifier']
                        rating_key = metadata['MediaContainer']['Metadata'][0]['ratingKey']
                        userRating = metadata['MediaContainer']['Metadata'][0]['userRating']
                        
                        if float(userRating) != float(stashRating):
                            rateQueryEncoded = urllib.urlencode({
                                "key": rating_key,
                                "identifier": identifier,
                                "rating": stashRating,
                                "X-Plex-Token": token
                            })
                            rateUrl = '{host}/:/rate?{rateQueryEncoded}'.format(
                                host=host,
                                rateQueryEncoded=rateQueryEncoded
                            )
                            if DEBUG:
                                Log('Rate request: %s' % rateUrl)
                            # inspired by https://github.com/pkkid/python-plexapi/blob/9b8c7d522d1ca94a0782b940c03d257d8dd071a0/plexapi/mixins.py#L317
                            request = urllib2.Request(url=rateUrl, data=urllib.urlencode({'dummy':'dummy'}), headers={
                                'Content-Type': 'text/html',
                            })
                            request.get_method = lambda: 'GET'
                            response = urllib2.urlopen(request)
                            if DEBUG:
                                Log("setUserRating: response: %s" % response.read())
                        else:
                            Log("User rating %s already set to %s" % (userRating, stashRating))
                    else:
                        Log("Media has no user rating, skipping")

            # Set the summary
            if data['details']:
                summary = data["details"].replace("\n", " ").replace("\r", "").replace("\t", "")
                metadata.summary = summary

            # Set series and add to collections
            if Prefs["CreateSiteCollectionTags"]:
                if not data["studio"] is None:
                    if Prefs["PrefixSiteCollectionTags"]:
                        SitePrefix = Prefs["PrefixSiteCollectionTags"]
                    else:
                        SitePrefix = "Site: "
                    site = SitePrefix + data["studio"]["name"]
                    try:
                        if DEBUG:
                            Log("Adding Site Collection: " + site)
                        metadata.collections.add(site)
                    except:
                        pass
            if Prefs["CreateStudioCollectionTags"]:
                if not data["studio"] is None:
                    if Prefs["PrefixStudioCollectionTags"]:
                        StudioPrefix = Prefs["PrefixStudioCollectionTags"]
                    else:
                        StudioPrefix = "Studio: "
                    if not data["studio"]["parent_studio"] is None:
                        site = StudioPrefix + data["studio"]["parent_studio"]["name"]
                    else:
                        if Prefs["UseSiteForStudioCollectionTags"]:
                            site = StudioPrefix + data["studio"]["name"]
                        else:
                            site = None
                    try:
                        if DEBUG:
                            Log("Adding Studio Collection: " + site)
                        if site:
                            metadata.collections.add(site)
                    except:
                        pass
            if Prefs["CreateMovieCollectionTags"]:
                if not data["movies"] is None:
                    for movie in data["movies"]:
                        if Prefs["PrefixMovieCollectionTags"]:
                            MoviePrefix = Prefs["PrefixMovieCollectionTags"]
                        else:
                            MoviePrefix = "Movie: "
                        if "name" in movie["movie"]:
                            movie_collection = MoviePrefix + movie["movie"]["name"]
                        try:
                            if DEBUG:
                                Log("Adding Movie Collection: " + movie_collection)
                            metadata.collections.add(movie_collection)
                        except:
                            pass
            if Prefs["CreatePerformerCollectionTags"]:
                if not data["performers"] is None:
                    for performer in data["performers"]:
                        if Prefs["CreatePerformerCollectionTags"]:
                            PerformerPrefix = Prefs["PrefixPerformerCollectionTags"]
                        else:
                            PerformerPrefix = "Actor: "
                        if "name" in performer:
                            actor_collection = PerformerPrefix + performer["name"]
                        try:
                            if DEBUG:
                                Log("Adding Performer Collection: " + actor_collection)
                            metadata.collections.add(actor_collection)
                        except:
                            pass

            # Add the genres
            metadata.genres.clear()
            if Prefs["IgnoreTags"]:
                ignore_tags = Prefs["IgnoreTags"].split(",")
                ignore_tags = list(map(lambda x: x.strip(), ignore_tags))
            else:
                ignore_tags = []
            if Prefs["CreateTagCollectionTags"]:
                collection_tags = Prefs["CreateTagCollectionTags"].split(",")
                collection_tags = list(map(lambda x: x.strip(), collection_tags))
            else:
                collection_tags = []
            try:
                if data["tags"]:
                    genres = data["tags"]
                    for genre in genres:
                        if not genre["id"] in ignore_tags and "ambiguous" not in genre["name"].lower():
                            metadata.genres.add(genre["name"])
                            if not Prefs["CreateAllTagCollectionTags"] and genre["id"] in collection_tags:
                                try:
                                    if DEBUG:
                                        Log("Adding Tag Collection: " + genre["name"])
                                    metadata.collections.add(genre["name"])
                                except:
                                    pass
                            elif Prefs["CreateAllTagCollectionTags"] and genre["id"] not in collection_tags:
                                try:
                                    if DEBUG:
                                        Log("Adding Tag Collection: " + genre["name"])
                                    metadata.collections.add(genre["name"])
                                except:
                                    pass
                if Prefs["AppendPerformerTags"]:
                    for performer in data["performers"]:
                        if performer["tags"]:
                            genres = performer["tags"]
                            for genre in genres:
                                if not genre["id"] in ignore_tags and "ambiguous" not in genre["name"].lower() and genre["name"] not in metadata.genres:
                                    if DEBUG:
                                        Log("Added Performer (" + performer['name'] + ") tag to scene: " + genre['name'] )
                                    metadata.genres.add(genre["name"])
                                    if genre["id"] in collection_tags:
                                        try:
                                            if DEBUG:
                                                Log("Adding Tag Collection: " + genre["name"])
                                            metadata.collections.add(genre["name"])
                                        except:
                                            pass
            except:
                pass

            # Add the performers
            metadata.roles.clear()
            # Create and populate role with actor's name
            try:
                if data["performers"]:
                    api_string = ""
                    if Prefs['APIKey']:
                        api_string = '&apikey=%s' % Prefs['APIKey']
                    models=data["performers"]
                    for model in models:
                        if DEBUG:
                            Log("Pulling Model: " + model["name"] + " With Image: " + model["image_path"])
                        role = metadata.roles.new()
                        role.name = model["name"]
                        role.photo = model["image_path"] + api_string
            except:
                pass

            # Add posters and fan art.
            if not data["paths"]["screenshot"] is None:
                api_string = ""
                if Prefs['APIKey']:
                    api_string = '&apikey=%s' % Prefs['APIKey']
                try:
                    thumb = HTTP.Request(data["paths"]["screenshot"] + api_string)
                    # TODO: see performance impact vs benefit of these two clear_ methods.
                    #  Seems to impact IO, and probably shouldn't be needed due to Plex removing old bundles every week.
                    #clear_posters(metadata)
                    #clear_art(metadata)
                    metadata.posters[data["paths"]["screenshot"] + api_string] = Proxy.Media(thumb, sort_order=0)
                    metadata.art[data["paths"]["screenshot"] + api_string] = Proxy.Media(thumb, sort_order=0)
                except Exception as e:
                    Log.Exception('Exception creating posters: %s' % str(e))
                    pass

            if Prefs["IncludeGalleryImages"]:
                api_string = ""
                if Prefs['APIKey']:
                    api_string = '&apikey=%s' % Prefs['APIKey']
                if Prefs['UseHTTPS']:
                    imagestring = 'https://%s:%s/image/%s/image' + api_string
                else:
                    imagestring = 'http://%s:%s/image/%s/image' + api_string
                if not data["galleries"] is None:
                    for gallery in data["galleries"]:
                        for image in gallery["images"]:
                            if Prefs["SortGalleryImages"]:
                                if image["file"]["height"] > image["file"]["width"]:
                                    image_orientation = "poster"
                                else:
                                    image_orientation = "background"
                            else:
                                image_orientation = "all"
                            imageurl = imagestring % (Prefs['Hostname'], Prefs['Port'], image["id"])
                            try:
                                thumb = HTTP.Request(imageurl)
                                if image_orientation == "poster" or image_orientation == "all":
                                    if DEBUG:
                                        Log("Inserting Poster image: " + image["title"] + " (" + str(image["file"]["width"]) + "x" + str(image["file"]["height"]) + " WxH)")
                                    metadata.posters[imageurl] = Proxy.Media(thumb)
                                if image_orientation == "background" or image_orientation == "all":
                                    if DEBUG:
                                        Log("Inserting Background image: " + image["title"] + " (" + str(image["file"]["width"]) + "x" + str(image["file"]["height"]) + " WxH)")
                                        metadata.art[imageurl] = Proxy.Media(thumb)
                            except Exception as e:
                                pass
