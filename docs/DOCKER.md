# Docker Quick Start

MUIOGO provides an **optional** Docker-based development environment.

This path is strictly additive.

## Prerequisites

| Platform | Requirement |
| --- | --- |
| Windows | Docker Desktop + WSL 2 enabled |
| macOS | Docker Desktop |
| Linux | Docker Engine + Docker Compose plugin |

## Installing Docker

If Docker is not already installed:

### Windows

- Install **Docker Desktop for Windows**:

  <https://docs.docker.com/desktop/setup/install/windows-install/>

- Requirements:
  - WSL 2 enabled (Windows Subsystem for Linux)
  - Recommended to run Linux containers (default)

- Verify WSL version:

    ```powershell
    wsl --version
    ```

- If WSL is not installed:

    ```powershell
    wsl --install
    ```

- Start Docker Desktop and wait until the Docker whale icon reports “Running.”

### macOS

- Install **Docker Desktop for macOS**:

  <https://docs.docker.com/desktop/setup/install/mac-install/>
- Launch Docker Desktop and wait until the Docker whale indicates “Running.”

### Linux

- Install Docker Engine + Compose plugin:

  <https://docs.docker.com/engine/install/ubuntu/>

- After installation, verify:

    ```bash
    docker --version
    docker compose version
    ```

- For other Linux distributions, see the official Docker installation guides:

  <https://docs.docker.com/engine/install/>

## Quick Start

### Start the App

```bash
docker compose up --build
```

- Builds the image and starts (foreground - logs stream to terminal)

Open <http://localhost:5002> in your browser.

### Run in detached mode (background)

```bash
docker compose up --build -d
```

#### View logs

```bash
docker compose logs -f
```

### Port Override

```bash
HOST_PORT=8080 docker compose up --build
```

Then open <http://localhost:8080>.

> Note: The app still runs on port 5002 inside the container.
> HOST_PORT only changes the external port on your machine.

## Development Mode (Live Reload)

For local development, you can run the app with live reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

- Source code is mounted into the container
- Changes to .py files reload automatically
- No rebuild needed for code changes

This uses Flask’s development server instead of waitress.
> Note: This mode is intended for development only.

## Stopping and Cleanup

```bash
# Stop containers - DataStorage volume is preserved
docker compose down

# Stop containers and remove the DataStorage volume (wipes all case data)
docker compose down -v
```

## Data Persistence

`WebAPP/DataStorage/` is stored in a named Docker volume `datastorage`.

Data persists across restarts.

- To wipe data: **`docker compose down -v`**

### Accessing Data Files from the Host

```bash
# Copy the entire DataStorage out of the volume to the host
docker compose cp api:/app/WebAPP/DataStorage ./datastorage-backup

# Open an interactive shell inside the running container
docker compose exec api sh
```

## Verifying Solvers

```bash
docker compose exec api glpsol --version
docker compose exec api cbc -stop
```

Both should print version information.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Port already in use | `HOST_PORT=8080 docker compose up --build` |
| App unreachable after `docker compose up --build -d` | `docker compose logs api` - wait for "MUIOGO API starting" |
| DataStorage empty after volume wipe | Restart with `docker compose up`; demo data is re-seeded automatically |
| Solver not found inside container | `docker compose build --no-cache` to force a clean install |
| Build fails on `apt-get` step | Ensure Docker Desktop is running; retry once (transient mirror issue) |
