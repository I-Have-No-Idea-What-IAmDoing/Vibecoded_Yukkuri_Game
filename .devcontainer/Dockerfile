FROM python:3.13-slim-bookworm

# System dependencies for pygame-ce (SDL2), pymunk (cffi), and pygame-render (OpenGL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libsdl2-gfx-dev \
    libffi-dev \
    libgl1 \
    libglx-mesa0 \
    libgles2-mesa-dev \
    libegl1-mesa-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Create non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

USER $USERNAME
