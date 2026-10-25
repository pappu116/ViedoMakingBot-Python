"""Every site selector lives here so a UI change only needs an edit in one place.

Each entry is a list of alternatives, tried in order — most specific first.
"""

YOUTUBE = {
    "create_button": [
        'button[aria-label="Create"]',
        'ytcp-button#create-icon',
        'button:has-text("Create")',
    ],
    "upload_menu_item": [
        'tp-yt-paper-item:has-text("Upload videos")',
        'ytcp-ve:has-text("Upload videos")',
        'text="Upload videos"',
    ],
    "file_input": [
        'input[type="file"][accept*="video"]',
        'input[type="file"]',
    ],
    "title_box": [
        'div#title-textarea textarea',
        'textarea[aria-label*="title" i]',
        'div#textbox[contenteditable="true"]',
    ],
    "description_box": [
        'div#description-textarea textarea',
        'textarea[aria-label*="description" i]',
        '#description-textarea div#textbox[contenteditable="true"]',
    ],
    "show_more": [
        'button:has-text("Show more")',
        'ytcp-button:has-text("Show more")',
    ],
    "tags_box": [
        'input[aria-label*="Tags" i]',
        'ytcp-form-input-container:has-text("Tags") input',
        '#tags-container input',
    ],
    "not_kids": [
        'tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]',
        'tp-yt-paper-radio-button:has-text("No, it\'s not made for kids")',
        'ytcp-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]',
    ],
    "next_button": [
        'ytcp-button#next-button',
        'button:has-text("Next")',
    ],
    "visibility_public": [
        'tp-yt-paper-radio-button[name="PUBLIC"]',
        'ytcp-radio-button[name="PUBLIC"]',
        'tp-yt-paper-radio-button:has-text("Public")',
    ],
    "visibility_unlisted": [
        'tp-yt-paper-radio-button[name="UNLISTED"]',
        'ytcp-radio-button[name="UNLISTED"]',
        'tp-yt-paper-radio-button:has-text("Unlisted")',
    ],
    "visibility_private": [
        'tp-yt-paper-radio-button[name="PRIVATE"]',
        'ytcp-radio-button[name="PRIVATE"]',
        'tp-yt-paper-radio-button:has-text("Private")',
    ],
    "publish_button": [
        'ytcp-button#done-button',
        'button:has-text("Publish")',
        'ytcp-button:has-text("Publish")',
        'button:has-text("Save")',
    ],
    "checks_complete": [
        'text="Checks complete"',
        'text="No issues found"',
        'ytcp-video-metadata-visibility:has-text("Public")',
    ],
    "dialog_title": [
        'ytcp-uploads-dialog',
        'ytcp-uploads-dialog:has-text("Details")',
    ],
    "video_link": [
        'a.ytcp-video-info',
        'a[href*="youtu.be"]',
        'a[href*="youtube.com/watch"]',
        'span:has-text("Video link")',
    ],
    "signed_in": [
        'button#avatar-btn',
        'ytcp-button#create-icon',
        'button[aria-label="Create"]',
    ],
    "account_picker": [
        'text="Choose an account"',
        'div[data-authuser]',
    ],
}

FACEBOOK = {
    "composer_openers": [
        'div[aria-label="Photo/video"]',
        'div[role="button"]:has-text("Photo/video")',
        'span:has-text("Photo/video")',
        'div[role="button"]:has-text("Photo/Video")',
    ],
    "file_input": [
        'input[type="file"][accept*="video"]',
        'input[type="file"]',
    ],
    "caption_box": [
        'div[role="dialog"] div[role="textbox"][contenteditable="true"]',
        'div[aria-label*="caption" i][contenteditable="true"]',
        'div[role="textbox"][contenteditable="true"]',
    ],
    "post_button": [
        'div[role="dialog"] div[aria-label="Post"]',
        'div[aria-label="Post"][role="button"]',
        'div[role="button"]:has-text("Post")',
        'div[role="button"]:has-text("Publish")',
    ],
    "reels_video_input": [
        'input[type="file"][accept*="video"]',
        'input[type="file"]',
    ],
    "reels_caption": [
        'div[contenteditable="true"][role="textbox"]',
        'textarea[placeholder*="description" i]',
    ],
    "reels_next": [
        'div[role="button"]:has-text("Next")',
        'div[aria-label="Next"]',
    ],
    "reels_publish": [
        'div[role="button"]:has-text("Publish")',
        'div[role="button"]:has-text("Post")',
        'div[aria-label="Publish"]',
    ],
    "logged_in_markers": [
        'div[aria-label="Your profile"]',
        'div[role="navigation"]',
        'div[aria-label="Create a post"]',
    ],
}
