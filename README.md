# GB Zelda AI Player

An AI system that plays The Legend of Zelda using PyBoy emulation, Azure OpenAI for decision-making, and local models for player control.

## Architecture

1. **PyBoy Integration**: Runs legitimate Zelda ROM and captures screen data
2. **Azure OpenAI**: Receives screen captures and makes strategic decisions
3. **Local Control**: Translates AI decisions into button presses using local models

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your Azure OpenAI credentials
```

3. Place your Zelda ROM file in the `roms/` directory

## Usage

```bash
python main.py
```

## Project Structure

- `src/`: Main source code
  - `pyboy_client.py`: PyBoy integration and ROM management
  - `azure_client.py`: Azure OpenAI communication
  - `screen_capture.py`: Screen capture and image processing
  - `local_controller.py`: Local model for button control
  - `main.py`: Main game loop orchestrator
- `roms/`: Directory for ROM files
- `logs/`: Logging output
- `models/`: Local model files