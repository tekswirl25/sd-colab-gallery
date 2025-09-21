# scripts/config.py

VARIANTS = {
    "SDXL": {
        "imports": [
            "StableDiffusionXLPipeline",
            "StableDiffusionXLImg2ImgPipeline",
            "StableDiffusionUpscalePipeline",
            "ControlNetModel",
            "StableDiffusionXLControlNetPipeline",
        ],
        "auto_upscale": False,
        "defaults": {
            "txt2img_steps": 30,
            "txt2img_cfg": 6.5,
            "img_size": (1024, 1024),
            "img2img_steps": 30,
            "img2img_cfg": 6.5,
            "controlnet_steps": 30,
            "controlnet_cfg": 6.5,
        }
    },
    "TURBO": {
        "imports": [
            "StableDiffusionXLPipeline",
            "StableDiffusionXLImg2ImgPipeline",
        ],
        "auto_upscale": False,
        "defaults": {
            "txt2img_steps": 4,
            "txt2img_cfg": 1.0,
            "img_size": (512, 512),
            "img2img_steps": 6,
            "img2img_cfg": 1.5,
            "controlnet_steps": 8,
            "controlnet_cfg": 1.5,
        }
    },
    "SD15": {
        "imports": ["DiffusionPipeline"],
        "auto_upscale": True,
        "defaults": {
            "txt2img_steps": 50,
            "txt2img_cfg": 7.5,
            "img_size": (512, 512),
            "img2img_steps": 50,
            "img2img_cfg": 7.5,
            "controlnet_steps": 50,
            "controlnet_cfg": 7.5,
        }
    }
}
