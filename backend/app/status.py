"""Shared status and type constants for the Agent Canvas runtime."""

NODE_TYPES = {
    "source_text",
    "story_segment",
    "script_block",
    "character_asset",
    "scene_asset",
    "prop_asset",
    "shot",
    "storyboard_grid",
    "audio_segment",
    "video_clip",
}

NODE_STATUS = {
    "pending",
    "waiting",
    "running",
    "done",
    "failed",
    "locked",
    "needs_review",
    "pending_image",
    "pending_grid",
    "pending_audio",
    "pending_video",
    "waiting_image",
    "waiting_grid",
    "waiting_audio",
    "waiting_video",
}

TASK_STATUS = {
    "pending",
    "running",
    "done",
    "failed",
    "timeout",
    "cancelled",
}

STAGES = [
    "style",
    "source",
    "script",
    "assets",
    "storyboard",
    "images",
    "audio",
    "video",
    "final",
]

DEFAULT_STYLE_ID = "ancient_live_action_realistic"
DEFAULT_GRID_MODE = "grid_4"
