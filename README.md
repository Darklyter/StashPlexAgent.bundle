# StashPlexAgent.bundle
A very simplistic (and very much a work in progress) Plex agent to pull metadata from Stash.

Scenes are matched based on filename (without path or extension), so files must be scanned into Stash with their current filename.

Preferences are set under the plugin, or in the library definition (if you set it as the primary agent for the library).  I'm using "Video Files Scanner" with it.

By default it will create Plex "Site: <STUDIO>" and "Studio: <STUDIO PARENT>" collection tags, but this can be disabled in preferences.  (If the studio doesn't have a parent then the primary studio will be used instead and be in both tags) 

Also Stash "Tags" are placed into Plex "Genres"

You can also set tag numbers to ignore on import, I've left mine in as an example.  You probably want to change these unless your "temporary" tags miraculously line up with mine. 

For installing just download the bundle and put it into your "\PlexMediaServer\Plex Media Server\Plug-ins" folder.  (The entire bundle as a directory...  "\StashPlexAgent.bundle")

I guarantee there will be problems.  When they pop up feel free to get with me on either the TPDB or Stash Discord channels.

Also this agent only handles scenes currently.  I haven't played with movies in Stash yet, but can take a look if there is interest.  Currently the Plex ADE agent handles that for me.

## Optional PlexSync Plugin
To further improve your Stash+Plex experience, you can install the optional "PlexSync" plugin in Stash.  This plugin automatically refreshes Plex's metadata for any scenes that are updated in Stash, so you don't ever need to run the resource-intensive "refresh all metadata" task in Plex.

See the [CommunityScripts/PlexSync](https://github.com/stashapp/CommunityScripts/blob/main/plugins/PlexSync/README.md) readme for the optional plugin's installation instructions.
