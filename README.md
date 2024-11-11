# LiveMEA

This project allows you to record live data from the LiveMEA service and save it to an HDF5 file. It provides both an API and a CLI for ease of use.

## Data specification

The live view gives, roughly every second, 4096 samples of data from 32 electrodes.

In the following code, each "duration" unit corresponds to 4096 values; the sampling frequency is 30kHz downsampled via wavelet transform by a factor of 8.

Therefore, a duration of 1 corresponds in reality to ~1.09 seconds of data.

Expect a disk usage of around 1.04 MB per second of recording, and an average wait time of 1.09 seconds per second of recording.

## Installation

1. Clone the repository:

    ```sh
    git clone <repository-url>
    cd live-mea
    ```

2. Install the required packages:

    ```sh
    pip install -r requirements.txt
    ```

## API Usage

### LiveMEA Class

#### Initialization

```python
from MEA_live import LiveMEA
from pathlib import Path

live_mea = LiveMEA(save_path: str | Path, recording_duration: int = 5, mea_id: int = 0)
```

- save_path
  (str | Path): Path to save the HDF5 file.
- recording_duration
 (int, optional): Duration of recording in seconds. Defaults to 5.
- mea_id
  (int, optional): MEA ID to use. Defaults to 0, must be between 0 and 3.

#### Methods

- record() : Starts recording live data and saves it to the specified HDF5 file.
- plot_data(h5f_path: str | Path): Plots data from an HDF5 file. Requires Matplotlib as an additional dependency.

### Example

```python
from MEA_live import LiveMEA

# Initialize the LiveMEA instance
live_mea = LiveMEA(save_path="live_data.h5", recording_duration=10, mea_id=1)

# Record data
live_mea.record()

# Plot recorded data
LiveMEA.plot_data("live_data.h5")
```

## CLI Usage

You can also use the CLI to record live MEA data.

### Command

From the repository directory, run the following command:

```sh
python live-mea -d <duration> -p <path> -m <MEA>
```

### Arguments

- `-d`, `--duration` (int, optional): Duration of the recording in seconds. Defaults to 5.
- `-p`, `--path` (str, optional): Path to save the recorded data. Defaults to "live_data.h5".
- `-m`, `--MEA` (int, optional): MEA ID to record data from. Defaults to 0.

### Example

```sh
python live-mea -d 10 -p "live_data.h5" -m 1
```

This command will record live MEA data for 10 seconds and save it to `live_data.h5` using MEA 1.

## Accessing the saved data

Each time point is saved under its own group in the HDF5 file. The data for each electrode is then saved as a dataset within the group.

The structure of the HDF5 file is as follows:

```plaintext
live_data.h5
├── timestamp_0
│   ├── electrode_0
│   ├── electrode_1
│   ├── ...
│   ├── electrode_31
├── timestamp_1
│   ├── ...
│   ├── electrode_31
├── ...
```

You can access the saved data using the `h5py` library in Python.

```python
import h5py

# Open the HDF5 file
with h5py.File("live_data.h5", "r") as f:
    # List all timestamps
    timestamps = list(f.keys())
    print("Timestamps:", timestamps)

    # Access data for a specific timestamp
    timestamp = timestamps[0]
    data_group = f[timestamp]

    # List all electrodes
    electrodes = list(data_group.keys())
    print("Electrodes:", electrodes)

    # Access data for a specific electrode
    electrode_data = data_group["electrode_0"][:]
    print("Electrode 0 data:", electrode_data)
```
