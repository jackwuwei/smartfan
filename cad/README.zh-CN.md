# CAD 源文件说明(build123d,参数化)

[English](README.md) | **简体中文**

整机与所有打印件都由这些 Python 脚本参数化生成。改参数 → 重新生成 → STEP(本目录)/ STL(`stl/`)一起更新。

## 1. 文件关系

```
rack_fan_2u.py        主文件:全部参数 + 几何函数 + 整机装配 gen_step()
   ├─ seg_left.py     薄包装 → make_segment() 切左段        (无自有参数)
   ├─ seg_mid.py      薄包装 → make_segment() 切中段        (无自有参数)
   ├─ seg_right.py    薄包装 → make_segment() 切右段        (无自有参数)
   └─ encoder_knob.py 独立旋钮件,自带一套参数;被主文件 import 进装配
```

- **改打印件的尺寸/孔位 → 基本都在 `rack_fan_2u.py` 顶部参数区。** 3 个薄包装文件只是"从整机里切出某一块",自己不带参数。
- `rack_fan_2u.py` 一改,4 个打印件都要重生成(它们 import 它)。
- 只有旋钮的轴配合在 `encoder_knob.py` 里单独调。

## 2. 坐标系(Z-up)

原点 = **面板前表面中心**。`X`=宽(右为+)、`Z`=高(上为+)、`Y`=深(+Y 指面板后方)。
CAD Viewer 也是 Z-up。`rack_fan_2u.step` 是**整机装配**(含风扇/Arduino 等占位体),只用于看整机、**不打印**。

## 3. 怎么生成

每个脚本都提供 `gen_step()`,返回一个 build123d 形体。所有命令在 `cad/` 下运行。

### 方式 A:用 `cad` agent skill

如果你装了 `cad` agent skill(并配好了它的 venv):

```bash
source ~/.agents/skills/cad/.venv/bin/activate
SKILL=~/.agents/skills/cad/scripts

# 整机装配(看整机用)
python $SKILL/step rack_fan_2u.py

# 单个打印件:生成 STEP(本目录)+ STL(放进 stl/)
python $SKILL/step seg_right.py        --force --stl stl/seg_right.stl
python $SKILL/step seg_left.py         --force --stl stl/seg_left.stl
python $SKILL/step seg_mid.py          --force --stl stl/seg_mid.stl
python $SKILL/step encoder_knob.py     --force --stl stl/encoder_knob.stl
```

### 方式 B:直接用 build123d

```bash
pip install build123d
```

然后在 `cad/` 下运行:

```python
import importlib
from build123d import export_step, export_stl

# 打印件:STEP + STL
for name in ["seg_left", "seg_mid", "seg_right", "encoder_knob"]:
    shape = importlib.import_module(name).gen_step()
    export_step(shape, f"{name}.step")
    export_stl(shape, f"stl/{name}.stl")

# 整机装配(仅供查看,不需要 STL)
import rack_fan_2u
export_step(rack_fan_2u.gen_step(), "rack_fan_2u.step")
```

> 改了 `rack_fan_2u.py` 的公共参数后,**4 个打印件都要重新跑**;只改 `encoder_knob.py` 则只重生成旋钮(和整机)。

## 4. `rack_fan_2u.py` 参数(全在文件顶部,mm 单位)

### 面板 / 机架
| 参数 | 默认 | 含义 / 改动影响 |
|---|---|---|
| `PANEL_W, PANEL_T, PANEL_H` | 482.6, 3.0, 88.1 | 19" 2U 面板 宽/厚/高(EIA-310,别动宽高) |
| `RACK_HOLE_DX` | 465.1/2 | 左右机架孔中心距的一半 |
| `RACK_HOLE_Z` | 38.1 | 每侧机架孔 Z(上下对称 ±38.1) |
| `RACK_SLOT_LEN, RACK_SLOT_H` | 11.0, 7.0 | 机架椭圆槽 X 长 / Z 高(长−高=±2mm 横向公差,M6) |

### 风扇
| 参数 | 默认 | 含义 / 改动影响 |
|---|---|---|
| `FAN` | 80.0 | 风扇边长(8025) |
| `FAN_BORE_D` | 76.0 | 面板进风开孔直径 |
| `FAN_HOLE_PITCH` | 71.5 | 4 个 M4 螺孔的方阵边距 |
| `FAN_HOLE_D` | 4.5 | M4 过孔直径 |
| `FAN_DEPTH` | 25.0 | 风扇厚度(仅占位体用) |
| `FAN_CX` | [-144, -29, 86] | **3 个风扇的 X 中心**。改它会动整机布局;与 `CTRL_CX` 一起决定 4 列等边距 |

### 控制列:OLED 窗 / 旋钮 / Arduino / 连接器
| 参数 | 默认 | 含义 / 改动影响 |
|---|---|---|
| `CTRL_CX` | 174.0 | **控制列 X 中心**(OLED 窗绕它)。注意 `ARD_CX`、`ENC_CX`、`SENS_CX` 是单独写的,改 `CTRL_CX` 时按需一起改 |
| `ARD_CX` | 165.0 | **Arduino X 中心**(从 `CTRL_CX` 左移 9):给右侧 DC 桶座/插头让空间;**再左会压到风扇1(主)**(左立柱≈X133,风扇1 右缘 X126) |
| `ARD_CZ` | 14.0 | Arduino Z 中心(翻装,板载点阵朝里不用,不需对窗) |
| `OLED_CZ` | 14.0 | OLED 窗 + 模块 Z 中心 |
| `OLED_WIN_W, OLED_WIN_H` | 25.0, 13.5 | 面板 OLED 开窗;窗中心 `OLED_WIN_CZ`=`OLED_CZ`+0.75 |
| `OLED_MOD_W/_T/_H` | 26.0, 5.0, 26.0 | OLED 模块 PCB 外形(占位 + 决定背面口袋大小) |
| `OLED_PIN_H` | 8.5 | OLED 4 针排针凸出(朝 +Y 走线) |
| `OLED_HOLE_DX` | 10.5 | OLED 4 角孔相对板心的 X(±10.5;实测 25×25 板,距两侧 2.0) |
| `OLED_HOLE_DZ_TOP, _BOT` | 11.0, -10.5 | 顶/底孔相对板心 Z(顶距顶边 1.5、底距底边 2.0) |
| `OLED_STANDOFF_H` | 2.0 | OLED 4 短立柱高(玻璃贴近窗;按实物玻璃高微调) |
| `OLED_STANDOFF_D` | 4.5 | OLED 立柱外径(M2) |
| `OLED_PILOT_D, OLED_PILOT_DEPTH` | 2.0, 4.0 | OLED 柱顶 M2 自攻引导孔(可深入面板) |
| `ENC_CX, ENC_CZ` | 174.0, -26.0 | 编码器(旋钮/轴)中心,在 OLED 窗下方(下移以让 KY-040 排针避开 Arduino 立柱) |
| `ENC_HOLE_D` | 7.2 | 编码器螺纹套筒过孔 ⌀7.2 |
| `ARD_W, ARD_T, ARD_L` | 68.6, 1.6, 53.4 | UNO R4 板 宽/厚/长(占位) |
| `ARD_STANDOFF_H` | 28.0 | Arduino 立柱高:翻装后焊接面朝面板,前方要容下 OLED 模块 + 排针/排线 |
| `HDR_H` | 8.5 | Arduino 母排针高(翻装后朝后;占位用,决定插杜邦线的间隙) |
| `STANDOFF_D` | 8.0 | Arduino 立柱外径 Ø8 |
| `ARD_PILOT_D, ARD_PILOT_DEPTH` | 2.0, 8.0 | Arduino 4 短柱**柱顶 M2 自攻引导孔**(板孔 Ø3.2 配 M2) |
| `ARD_HOLES` | 见文件 | **4 个安装孔相对板心的 (x,z)**。当前是**翻装**版(元件面/母排针朝 +Y 后侧、USB/DC 短边仍朝 +X)。若要改装板朝向,孔位要随之翻转(见 §6)。 |
| `DC_JACK_D/LEN`、`DC_PLUG_D/LEN`、`USB_*`、`CONN_DC_Z/USB_Z` | 见文件 | 接口短边上的 DC 桶座 / 代表性直插头 / USB-C 占位,**仅用于校核直插间隙**,不是结构件 |

> ⚠️ **两个关键朝向约束**:① 元件面/母排针朝 **+Y(后侧)**——才有空间插杜邦线;② USB/DC 短边朝 **+X(面板右开口端)**——才能直插 DC 桶座。详见根目录 `README.zh-CN.md` 装配要点第 4 步。

> 🔌 **模块直连**:OLED/DS18B20/KY-040 用 2 根「1分3」杜邦线(5V/GND 各一)直连 Arduino,面板上无分线板/托盘等承载结构。

### 传感器 / 走线
| 参数 | 默认 | 含义 |
|---|---|---|
| `SENS_CX, SENS_CZ` | 145.0, -33.0 | DS18B20 模块卡座中心(控制区下方空位) |
| `MOD_W, MOD_H, MOD_T` | 28.2, 13.0, 4.0 | DS18B20 PCB 模块外形(实测,决定卡座大小) |
| `SENS_HOLE_DX` | 6.4 | 温度板固定孔距左边缘(上下居中);卡座底板上开 M2.5 自攻孔 |
| `SENS_PILOT_D` | 2.2 | M2.5 自攻引导孔径 |
| `VENT_ZS` | () | 控制区散热缝(留空=不开;若要加须避开旋钮 ⌀16 @ `ENC_CZ`) |
| `CABLE_TIE_X` | () | 底沿扎带孔(留空=不开) |

### 分段打印 + M3 连接
| 参数 | 默认 | 含义 / 改动影响 |
|---|---|---|
| `SEAM1, SEAM2` | -86.5, 28.5 | **两条切缝 X**。必须落在风扇之间的实心区;且每段宽度 ≤ 256(P1S 床) |
| `WALL_T` | 6.0 | 每侧连接壁厚(X 向) |
| `WALL_Y0, WALL_Y1` | 3.0, 18.0 | 连接壁在面板后方的 Y 范围(深 15mm) |
| `WALL_Z` | 84.0 | 连接壁高(近满高) |
| `GROOVE_W, GROOVE_D` | 4.0, 2.2 | 对齐舌槽 Y 向宽 / X 向深(凸舌已自动留间隙) |
| `BOLT_YS, BOLT_ZS` | (6,15),(-28,28) | 每缝 4 颗 M3 的 Y、Z 位置(舌槽上下 × 两排) |
| `M3_CLEAR_R` | 1.75 | M3 过孔半径(⌀3.5) |

## 5. `encoder_knob.py` 参数(独立旋钮)

| 参数 | 默认 | 含义 / 改动影响 |
|---|---|---|
| `SHAFT_D` | 6.0 | 编码器**轴径**(圆)。按实物改 |
| `SHAFT_FLAT_ACROSS` | 4.8 | D 形轴**平面到对边**的厚度。按实物改 |
| `SHAFT_EXPOSED` | 14.0 | 拧好螺母后轴露出面板前表面的长度;决定孔深和旋钮高度 |
| `FIT_CLEAR` | 0.3 | 孔的打印间隙(0.2~0.4 调松紧;偏紧调大) |
| `TIP_CLEAR` | 0.5 | 轴尖到孔底留空,保证旋钮压到面板而不是顶在轴尖上 |
| `NUT_BORE_D, NUT_BORE_H` | 12.2, 3.0 | 底面沉孔 直径 / 深度,让开 M7 固定螺母(KY-040 无垫片) |
| `KNOB_D` | 16.0 | 旋钮外径(下限由 `NUT_BORE_D` 决定;沉孔一圈壁厚 ≈1.9mm) |
| `BORE_DEPTH` | 14.5(派生) | 从底面算起的孔深 = `SHAFT_EXPOSED` + `TIP_CLEAR` |
| `TOP_WALL` | 2.5 | 孔顶壁厚(刻掉指示线后仍留 1.5mm 实体) |
| `KNOB_H` | 17.0(派生) | 旋钮高 = `BORE_DEPTH` + `TOP_WALL` |
| `N_FLUTE, FLUTE_D` | 14, 2.2 | 侧面防滑槽数量 / 单槽直径(只开在沉孔以上) |
| `IND_W, IND_DEPTH` | 1.4, 1.0 | 顶面指示线宽 / 深 |

> 换了别的编码器,主要核对 `SHAFT_D` / `SHAFT_FLAT_ACROSS`(轴的圆径与 D 面)和 `SHAFT_EXPOSED`,压不进就把 `FIT_CLEAR` 调大。

## 6. 改参数的几条联动提醒

1. **控制列整体平移**:`CTRL_CX` 改了,记得 `ENC_CX`(默认同 174)和 `SENS_CX`(独立 145)按需跟着改;并检查右机架槽(X=`RACK_HOLE_DX`≈232.6)不被撞。
2. **Arduino 装板朝向**:`gen_step` 里 Arduino 用 `Rot(180,0,0)` 翻装(元件面/母排针朝 +Y 后侧、焊接面朝面板),`ARD_HOLES` 已配套翻好。前显示因此改用 **OLED**(`OLED_*` 参数 + 固件 `Adafruit_SSD1306`),不再用板载点阵。要动朝向就把这几样一起改。
   - 翻装后立柱必须够高(`ARD_STANDOFF_H`)容下前方 OLED+排针——母排针朝后,杜邦线直接插。
3. **切缝**:`SEAM1/SEAM2` 落在风扇之间实心区,且每段 ≤256mm。
4. 改完务必**重生成并在 Viewer 里目检**(尤其孔位/间隙),deterministic 检查通过不代表没撞。
