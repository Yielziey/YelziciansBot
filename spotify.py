import requests
import discord
from discord.ui import View, Button
import os

SPOTIFY_ARTIST_ID = "6rhenHsRHjPnQIcawW67VQ"  # Default artist for auto release

def get_spotify_token():
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
    url = "https://accounts.spotify.com/api/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET
    }
    response = requests.post(url, headers=headers, data=data)
    return response.json().get("access_token")


def get_latest_albums(artist_id, token, limit=5):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/albums"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"include_groups": "album,single", "limit": limit*2, "market": "US"}
    response = requests.get(url, headers=headers, params=params)
    albums_data = response.json().get("items", [])
    latest_albums = []

    for album in albums_data:
        album_url = f"https://api.spotify.com/v1/albums/{album['id']}"
        album_res = requests.get(album_url, headers=headers).json()
        track_count = album_res.get("total_tracks", 0)
        if track_count >= 3:
            album_name = album["name"]
            album_link = album["external_urls"]["spotify"]
            latest_albums.append(f"📀 [{album_name}]({album_link}) ({track_count} tracks)")
        if len(latest_albums) >= limit:
            break

    return latest_albums


def create_spotify_artist_embed(artist_data, top_tracks, latest_albums):
    from bot import ROLE_MENTION
    embed = discord.Embed(
        title=artist_data.get("name", "Artist"),
        url=artist_data.get("external_urls", {}).get("spotify"),
        description=f"{ROLE_MENTION}\n🎵 Discover this artist on Spotify!",
        color=0x1DB954
    )
    if artist_data.get("images"):
        embed.set_thumbnail(url=artist_data["images"][0]["url"])
    embed.add_field(name="👥 Followers", value=f"{artist_data.get('followers', {}).get('total', 0):,}", inline=True)
    embed.add_field(name="🎸 Genres", value=", ".join(artist_data.get("genres", [])) or "N/A", inline=True)
    embed.add_field(name="🔥 Top Songs", value="\n".join(top_tracks) if top_tracks else "No tracks found.", inline=False)
    embed.add_field(name="📀 Latest Albums", value="\n".join(latest_albums) if latest_albums else "No albums found.", inline=False)
    embed.set_footer(text="Powered by Spotify API 🎶", icon_url="https://cdn-icons-png.flaticon.com/512/2111/2111624.png")
    return embed


def get_artist_latest_album(token):
    url = f"https://api.spotify.com/v1/artists/{SPOTIFY_ARTIST_ID}/albums"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"include_groups": "album,single", "limit": 1, "market": "US"}
    res = requests.get(url, headers=headers, params=params).json()
    if res.get("items"):
        return res["items"][0]
    return None


def create_spotify_view(artist_data):
    """Create Discord UI View with Open in Spotify button"""
    view = View()
    spotify_url = artist_data.get("external_urls", {}).get("spotify")
    if spotify_url:
        view.add_item(Button(label="Open in Spotify", url=spotify_url, style=discord.ButtonStyle.link))
    return view
