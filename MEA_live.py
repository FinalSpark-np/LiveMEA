import asyncio
import socketio
import aiohttp
import numpy as np
import h5py
from datetime import datetime, UTC
from pathlib import Path


class LiveMEA:
    SERVER_URL = "https://livemeaservice2.alpvision.com"
    MAX_QUEUE_SIZE = 100
    DEFAULT_DURATION = 5

    def __init__(
        self, save_path: str | Path, recording_duration: int = 5, mea_id: int = 0
    ):
        """This class lets you obtain live data from the LiveMEA service and save it to an HDF5 file.

        Feel free to adapt the code to your needs, especially the "record" method.

        Args:
            recording_duration (int, optional): Duration of recording in seconds. Defaults to 5.
            save_path (str, optional): Path to save the HDF5 file. Defaults to "live_data.h5".
            mea_id (int, optional): MEA ID to use. Defaults to 0, must be between 0 and 3.

        Attributes:
            save_path (Path): Path to save the HDF5 file.
            duration (float): Duration of recording in seconds.
            mea_id (int): MEA ID to use.
            sio (socketio.AsyncClient): SocketIO client.
            queue (asyncio.Queue): Queue to store data.
            mea_id (int): MEA ID to use
        """
        self._save_path = None
        self._duration = None
        self._meaid = mea_id
        ###
        self.sio = socketio.AsyncClient()
        self.queue = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self.duration = recording_duration
        path = Path(save_path)
        self.save_path = path
        self.mea_id = mea_id

    @property
    def save_path(self):
        return self._save_path

    @save_path.setter
    def save_path(self, path):
        path = Path(path)
        self._save_path = path if path.suffix == ".h5" else path.with_suffix(".h5")

        if path.exists():
            raise FileExistsError(
                f"{path} already exists and would be overwritten by new data. Please choose a different path."
            )

        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, duration):
        if duration <= 0:
            raise ValueError("Duration must be greater than 0")
        self._duration = duration

    @property
    def mea_id(self):
        return self._meaid

    @mea_id.setter
    def mea_id(self, meaid):
        if not isinstance(meaid, int):
            raise ValueError("MEA ID must be an integer")
        if meaid not in range(0, 4):
            raise ValueError("MEA ID must be in the range 0-3")
        self._meaid = meaid

    async def _fetch_http_data(self, session, endpoint):
        try:
            async with session.get(f"{self.SERVER_URL}{endpoint}") as response:
                if response.headers["Content-Type"] == "application/json":
                    return await response.json()
                else:
                    return await response.text()
        except asyncio.CancelledError:
            print(f"HTTP data fetch for {endpoint} was cancelled")
            raise

    async def _fetch_all_http_data(self):
        try:
            async with aiohttp.ClientSession() as session:
                check_service = await self._fetch_http_data(session, "/check")
                is_live = await self._fetch_http_data(session, "/islive")
                default_mea = await self._fetch_http_data(session, "/defaultmea")

                status = f"{check_service}"
                if is_live:
                    status += " - Live"
                else:
                    status += " - Offline"
                    raise Exception("LiveMEA service is offline")
                print(f"Status - {status}")
                print("Default MEA:", default_mea[-2])

        except asyncio.CancelledError:
            print("fetch_all_http_data was cancelled")
            raise

    async def _listen_socket_events(self):
        @self.sio.event
        async def livedata(data):
            buffer = data["buffer"]
            data = np.frombuffer(buffer, dtype=np.float32)
            # data is 4096 points x 32 electrodes
            elec_data = data.reshape(32, 4096)
            if self.queue.full():
                self.queue.get_nowait()
            await self.queue.put((datetime.now(UTC), elec_data))
            print(f"{self.queue.qsize()} / {int(self.duration)}", end="\r")

        await self.sio.connect(self.SERVER_URL)
        await self.sio.emit("meaid", self.mea_id)
        try:
            while self.queue.qsize() < self.duration:
                # res = await self.sio.wait()
                await self.sio.sleep(0.5)
        except asyncio.CancelledError:
            print("listen_socket_events was cancelled")
            await self.sio.disconnect()
            raise

    async def _start_async_loop(self, duration):
        tasks = [
            self._fetch_all_http_data(),
            self._listen_socket_events(),
        ]
        try:
            while self.queue.qsize() < duration:
                await asyncio.gather(*tasks)
        except asyncio.TimeoutError:
            print("Async loop completed after timeout")
        except asyncio.CancelledError:
            print("Recording finished")
            raise
        finally:
            await self.sio.disconnect()

    def _save_data(self, data, file_path):
        with h5py.File(file_path, "w") as f:
            for timestamp, elec_data in data.items():
                grp = f.create_group(str(timestamp))
                for elec, data in elec_data.items():
                    grp.create_dataset(elec, data=data)
            print("Data saved to live_data.h5")

    async def _record_live_data(self, duration):
        try:
            await self._start_async_loop(duration)
        except asyncio.TimeoutError:
            raise
        except asyncio.CancelledError:
            print("Recording live data was cancelled")
            raise

        data = {}
        while not self.queue.empty():
            timestamp, elec_data = await self.queue.get()
            data[timestamp] = {
                f"electrode_{i}": elec_data[i].tolist() for i in range(32)
            }
            self.queue.task_done()

        self._save_data(data, self.save_path)
        return data  # if you only need the data, disable the save_data method and use the return statement

    def record(self, duration: int = None, save_path: str | Path = None):
        """Record live data from the LiveMEA service and save it to an HDF5 file.

        Args:
            duration (int, optional): Duration of recording in seconds. Defaults to None.
            save_path (str | Path, optional): Path to save the HDF5 file. Defaults to None.
        """
        if duration:
            self.duration = duration
        if save_path:
            self.save_path = save_path
        try:
            return asyncio.run(self._record_live_data(self.duration))
        except Exception as e:
            print(f"An error occurred: {e}")

    @classmethod
    def quick_record(cls, save_path: str, duration: int = 5, mea_id: int = 0):
        """
        Quick method to record live data and save it to an HDF5 file.

        Args:
            save_path (str): Path to save the HDF5 file.
            duration (int, optional): Duration of recording in seconds. Defaults to 5.
            mea_id (int, optional): MEA ID to use. Defaults to 0, must be between 0 and 3.

        Returns:
            LiveMEA: Instance of LiveMEA class.
            dict: Data recorded.
        """
        live_mea = cls(recording_duration=duration, save_path=save_path, mea_id=mea_id)
        data = live_mea.record()
        return live_mea, data

    @staticmethod
    def plot_data(h5f_path: str | Path):
        """Plot data from an HDF5 file."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ModuleNotFoundError("Matplotlib is required for plotting")
        h5_file_path = Path(h5f_path)
        with h5py.File(h5_file_path, "r") as f:
            timestamps = sorted(f.keys(), key=lambda x: str(x))
            num_channels = 32
            fig, axes = plt.subplots(num_channels, 1, figsize=(15, 30), sharex=True)

            for i in range(num_channels):
                all_data = []
                for timestamp in timestamps:
                    channel_data = f[timestamp][f"electrode_{i}"][:]
                    all_data.extend(channel_data)
                axes[i].plot(all_data)
                axes[i].set_title(f"Electrode {i}")

            plt.xlabel("Time")
            plt.tight_layout()
            plt.show()


# Example usage
if __name__ == "__main__":
    live_mea = LiveMEA(recording_duration=1, save_path="live_data.h5")
    data = live_mea.record()
    LiveMEA.plot_data("live_data.h5")
