def dysi(input: str) -> bool:
    sanitized_input = input.replace(".", "")
    return "727" in sanitized_input


def get_username(link):
    parts = link.split("/")
    return parts[-1]


def extract_socials(json_obj):
    twitter_link = None
    twitch_link = None
    youtube_link = None
    beatsaver_link = None
    for item in json_obj:
        service = item.get('service')
        link = item.get('link')
        
        if service and link:
            if service == 'Twitter':
                twitter_link = link
            elif service == 'Twitch':
                twitch_link = link
            elif service == 'YouTube':
                youtube_link = link
            elif service == 'BeatSaver':
                beatsaver_link = link
                
    return twitter_link, twitch_link, youtube_link, beatsaver_link
