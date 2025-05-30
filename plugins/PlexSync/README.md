# Stash Plugin updating your Plex metadata automatically

This plugin solves the problem of "I have many files in my Plex, but they don't get any of the changes I do in Stash, and doing a `refresh all metadata` takes too much time".

With this, Stash behaves as the main source for all your Stash scenes in Plex, and it keeps Plex in sync with changes done via Stash.

# Install

Install the plugin in Stash first, and then install the updated Stash-Plex-Agent.

## Stash side

1. Create a folder in your Stash plugins with whatever name you want.

2. Add the PlexSync.py and requirements.txt files there.

3. **IMPORTANT**: edit the variables in PlexSync.py (lines 11 to 22).

4. Install the python requirements however you want (I personally go into the folder and run `python3 -m pip install -r requirements.txt -t .`)

5. Go in Stash UI and see that plugin is active there.

## Plex side

Do this *after* making sure the Stash side is complete.

1. After installing the newest version of this agent, make sure that `AddPlexURL` is enabled ("Adds the Plex media ID to the scene in Stash; allows Stash to update Plex metadata.")

2. Refresh all metadata in Plex for the libraries using this agent.

Now, you should see scenes being updated in Stash, adding this URL to the scenes: `plex/library/metadata/12345` (12345 being the metadata ID of the scene in Plex)

# Usage

Update your scenes in Stash like normal, and these scenes will be automatically refreshed in Plex. 🎉

# Warnings
- Titles will be processed with `unidecode` if you enable the "clean titles" setting.  This means that all non-ASCII characters in your titles will be converted; Cyrillic script for example will be taken away.

- The plugin connects to your Plex via TLS, but it ignores cert errors.  But this is not really a problem, as your Stash is most likely on the same host as your Plex...
