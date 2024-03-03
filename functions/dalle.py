DALLE_FUNCTION = {
    "type": "function",
    "function": {
        "name": "getDalleImages",
        "description": "Given two potential life paths, help the user visualize the potential future through generating images from DALL-E.",
        "parameters": {
            "type": "object",
            "properties": {
            "prompt": {
                "type": "string", 
                "description": "A descriptive prompt to generate images from the user's perspective."
                },
            "path_num": {
                "type": "string",
                "enum": ["1", "2"],
                "description": "The path which is being visualized with the prompt"
            }
        },
        "required": ["prompt"]
      }
    }
  }