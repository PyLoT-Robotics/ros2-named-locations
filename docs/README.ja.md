# ROS 2 Named Locations

[English](../README.md) · 日本語

ロボットの位置を名前付きで記録・照会し、初期位置配信やNav2の移動先に利用します。
元のSpotRecorderとPositionRecorderを1つの保存形式とフレーム指定に整理しました。

## 地点データの管理

```bash
ros2-named-locations --file locations.yaml add entrance --x 1.0 --y 2.0 --yaw 0.5
ros2-named-locations --file locations.yaml list
ros2-named-locations --file locations.yaml show entrance
```

座標はm、yawはrad。各地点はframe_idを持ち、既定はmapです。同名への上書きは
`--replace` が必要です。`delete NAME` で削除できます。保存形式は
`{schema_version: 1, locations: {NAME: {x: ..., y: ..., yaw: ..., frame_id: map}}}`。
旧spots.yaml形式は自動では読み込みません。複数ファイルを暗黙に混在させません。

保存はLinuxのファイルロックとatomic renameを使用し、並行記録で地点が消えることを
防ぎます。不正な既存ファイルを検出した場合は上書きせずエラーにします。

## ROSでの記録と移動

```bash
ros2-named-locations --file locations.yaml record entrance --frame map --base base_link
ros2-named-locations --file locations.yaml initialpose entrance
ros2-named-locations --file locations.yaml go entrance --timeout 60
```

`record` は現在TFを記録します。動的TFの鮮度を確認し、静的TFのstamp=0は許容します。
`initialpose` は購読者を待って `/initialpose` に1回配信します。
`go` は `/navigate_to_pose` を呼び、結果の成功を確認します。期限超過はキャンセルを
要求してエラー終了します。コマンドの期限は `--timeout` で指定できます。

常駐ノードは `file`, `labels`, `frame_id`, `base_frame`, `max_tf_age_sec` を設定して起動します。
既定ラベルstart/entranceの場合、次のTriggerサービスを公開します。

- `/named_locations/record_start`, `/named_locations/record_entrance`
- `/named_locations/initialpose_start`, `/named_locations/initialpose_entrance`
- `/named_locations/list`（JSONで地点を返す）

常駐ノードの上書きは `replace_existing:=true` を明示した場合だけです。
地点記録時はTFがまだ到着していなければサービス失敗を返すので、配信開始後に再試行してください。
起動だけではナビゲーションも初期位置配信も行いません。

## インストールと検証

Python 3.10+。リポジトリのルートで実行します。通常のPython環境ではROSは不要です。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python -m named_locations.cli demo
```

ROS 2 Jazzyで使う場合は通常のワークスペースのsrcに配置し、ROS環境でビルドします。

```bash
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select named_locations
source install/setup.bash
```

`config/params.yaml` を自分の入出力に合わせて変更してください。パラメータは起動時設定です。
`ros2 launch named_locations named_locations.launch.py params_file:=/absolute/path/to/params.yaml` で起動できます。
CIはPython 3.10/3.12でコアテストと合成デモを実行します。ROS結合テストはROS環境で
実行し、それ以外ではスキップします。モデル・実センサ・実アームの性能は認証しません。

## ライセンスと出典

現在はprivateリポジトリです。Apache-2.0。元のコミット・ファイルと変更範囲は
[PROVENANCE.md](../PROVENANCE.md) を参照してください。元モノレポへの依存はありません。
