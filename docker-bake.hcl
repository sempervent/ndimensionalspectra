variable "REGISTRY" {
    default = "ghcr.io/your-org"
}

variable "IMAGE_BASE" {
    default = "ndimensionalspectra"
}

variable "VERSION" {
    default = "0.1.0"
}

variable "PLATFORMS" {
    default = "linux/amd64,linux/arm64"
}

group "default" {
    targets = ["api", "ui", "nginx"]
}

group "push" {
    targets = ["api-push", "ui-push", "nginx-push"]
}

target "api" {
    context = "."
    dockerfile = "Dockerfile.api"
    platforms = split(",", PLATFORMS)
    tags = [
        "${REGISTRY}/${IMAGE_BASE}-api:${VERSION}",
        "${REGISTRY}/${IMAGE_BASE}-api:latest"
    ]
}

target "api-push" {
    inherits = ["api"]
    output = ["type=registry"]
}

target "ui" {
    context = "."
    dockerfile = "Dockerfile.ui"
    platforms = split(",", PLATFORMS)
    tags = [
        "${REGISTRY}/${IMAGE_BASE}-ui:${VERSION}",
        "${REGISTRY}/${IMAGE_BASE}-ui:latest"
    ]
}

target "ui-push" {
    inherits = ["ui"]
    output = ["type=registry"]
}

target "nginx" {
    context = "."
    dockerfile = "Dockerfile.nginx"
    platforms = split(",", PLATFORMS)
    tags = [
        "${REGISTRY}/${IMAGE_BASE}-nginx:${VERSION}",
        "${REGISTRY}/${IMAGE_BASE}-nginx:latest"
    ]
}

target "nginx-push" {
    inherits = ["nginx"]
    output = ["type=registry"]
} 