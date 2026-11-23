# ROS 2 Named Locations

English · [日本語](docs/README.ja.md)

Record and query named robot locations, publish initial poses and use saved
locations as Nav2 goals. The original SpotRecorder and PositionRecorder are
consolidated into one storage format with explicit coordinate frames.

## Offline location library

```bash
ros2-named-locations --file locations.yaml add entrance --x 1.0 --y 2.0 --yaw 0.5
ros2-named-locations --file locations.yaml list
ros2-named-locations --file locations.yaml show entrance
```

Coordinates are in metres and yaw is in radians. Each location has a `frame_id`,
which defaults to map. Overwriting an existing name requires `--replace`;
`delete NAME` removes it. The storage format is
`{schema_version: 1, locations: {NAME: {x: ..., y: ..., yaw: ..., frame_id: map}}}`.
Legacy spots.yaml files are not read automatically, and multiple formats are
not silently mixed.

Writes use Linux file locking and atomic rename so concurrent records do not
lose other locations. Invalid existing files cause an error rather than being
overwritten.

## ROS recording and navigation

```bash
ros2-named-locations --file locations.yaml record entrance --frame map --base base_link
ros2-named-locations --file locations.yaml initialpose entrance
ros2-named-locations --file locations.yaml go entrance --timeout 60
```

`record` captures the current TF. Dynamic transforms must be fresh; a static
transform with stamp=0 is allowed. `initialpose` waits for a subscriber and
publishes once on `/initialpose`. `go` calls `/navigate_to_pose` and checks the
result for success. On timeout it requests cancellation and exits with an error.
Set the command deadline with `--timeout`.

Configure the persistent node with `file`, `labels`, `frame_id`, `base_frame`
and `max_tf_age_sec`. With the default start/entrance labels it provides these
Trigger services:

- `/named_locations/record_start`, `/named_locations/record_entrance`
- `/named_locations/initialpose_start`, `/named_locations/initialpose_entrance`
- `/named_locations/list`, which returns locations as JSON.

The persistent node overwrites names only when `replace_existing:=true` is set
explicitly. A recording service returns failure if TF has not arrived yet;
retry once transforms are available. Starting the node does not navigate or
publish an initial pose.

## Installation and checks

Requires Python 3.10+. Run these commands from the repository root.
The core works in a regular Python environment without ROS.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python -m named_locations.cli demo
```

For ROS 2 Jazzy, place the repository in a regular workspace's `src` directory
and build it in a ROS environment:

```bash
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select named_locations
source install/setup.bash
```

Adapt `config/params.yaml` to your inputs and outputs. Parameters are read at startup.
Start the node with
`ros2 launch named_locations named_locations.launch.py params_file:=/absolute/path/to/params.yaml`.
CI runs core tests and the synthetic demo on Python 3.10 and 3.12. ROS integration
tests run when ROS is available and are skipped otherwise. These checks do not
certify model, physical-sensor or real-arm performance.

## License and source

Apache-2.0. See
[PROVENANCE.md](PROVENANCE.md) for the source commit, files and extraction changes.
There is no dependency on the original monorepo.
