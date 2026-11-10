# 画师 tag 实测清单（Anima / danbooru）

> 生成于 2026-11-10 01:57，数据源 `_setup/danbooru.csv`（140,782 条 tag，其中 artist 类 59,201 条）。
> 括号里的数字是 danbooru 上挂在该画师 tag 下的作品数——**它就是模型训练时见过的张数**。

## 一、为什么现在的画师 tag「写了没用」

1. **工坊 `wb_tags.json` 的画师组里有 79/111 个 danbooru 根本不存在**（`greg rutkowski`、`artgerm`、`moebius`、`alphonse mucha`、`hayao miyazaki`、`tite kubo`…）。这些是西方插画师/动画导演的名字，danbooru 不用这套命名，模型自然没有对应权重——写进去等于噪声。
2. **存在的那些写法也要对**：danbooru 用下划线 + 括号消歧义，`ask (artist)` 必须写 `ask_(askzy)`，`wada arco` → `wada_arco`，`kantoku` 才是 `kantoku`。
3. **单个画师 tag 在 2B 蒸馏模型里权重很弱**。Anima 把上万画师压进 2B 参数，风格被平均得很厉害；一个 tag 只够「轻轻偏一下」，看起来就像没用。社区做法是**2–3 个同风格画师叠加 + 明确权重**。
4. **位置**：画师 tag 要放在质量词之后、角色 tag 之前。放最末尾会被角色/场景词稀释。
5. **别和 character tag 抢**：角色 tag（`hakurei_reimu`）本身自带官方画风，会和画师 tag 打架；要风格就先低权重试，或者干脆不写角色、只写外观。

## 二、正确用法（照这个写）

```
masterpiece, best quality, (artist_a:1.15), (artist_b:1.1), artist_c,
1girl, solo, <角色或外观>, <动作>, <场景>, <光>
```

- **2–3 个画师**：少于 2 个几乎看不出；多于 3 个会糊成一团、丢细节。
- **权重 1.1–1.25**：先 `(tag:1.15)`，效果过冲就降到 1.05；不要给到 1.4 以上（会出油画糊）。
- **同风格才叠**：厚涂 + 厚涂、赛璐璐 + 赛璐璐；混着叠会互相抵消。
- **反向要写 `(artist_name:1.2)` 到负面**只在你确实想甩掉某个风格时用，别乱加。
- 想更稳可以配一个风格词：`impasto`（厚涂）/ `flat_color`（平涂）/ `lineart` / `monochrome` / `limited_palette`——这几个都在词表里，等于给画师 tag 一个「落点」。

## 三、清单（按 danbooru 作品数，越上面模型越熟）

### A 档 · ≥2500 张（最稳，优先用这些）33 个

- ebifurya(5924) · hammer_(sunset_beach)(5418) · haruyama_kazunori(5230)
- itomugi-kun(4518) · mizuki_hitoshi(4312) · kouji_(campus_life)(4281)
- yaegashi_nan(4026) · kanon_(kurogane_knights)(3950) · ruu_(tksymkw)(3891)
- naga_u(3562) · kou_hiyoyo(3454) · tani_takeshi(3411)
- bkub(3365) · rebecca_(keinelove)(3234) · tony_taka(3146)
- ojipon(3108) · matsunaga_kouyou(3068) · blade_(galaxist)(3062)
- bow_(bhp)(2983) · ixy(2937) · a1_(initial-g)(2936)
- hara_(harayutaka)(2932) · ido_(teketeke)(2828) · chihuri(2802)
- bb_(baalbuddy)(2755) · futa_(nabezoko)(2750) · hiroki_(yyqw7151)(2610)
- hisahiko(2605) · yohane(2589) · hews(2579)
- hungry_clicker(2567) · dd_(ijigendd)(2563) · kirisawa_juuzou(2538)

### B 档 · 2000–2500 张（稳，可当第二/第三张牌）36 个

- zounose(2493) · carnelian(2477) · m-da_s-tarou(2467)
- warugaki_(sk-ii)(2446) · boris_(noborhys)(2408) · shiseki_hirame(2395)
- hamu_koutarou(2381) · rariatto_(ganguri)(2379) · kani_biimu(2367)
- houtengeki(2359) · minaba_hideo(2336) · abubu(2335)
- kantoku(2331) · ishiyumi(2309) · slugbox(2300)
- iesupa(2299) · tsukishiro_saika(2270) · ichimi(2267)
- nanashi_(nlo)(2262) · nyantcha(2260) · hisona_(suaritesumi)(2255)
- avogado6(2232) · yua_(checkmate)(2213) · kouno_(masao)(2177)
- sofra(2170) · yukie_(kusaka_shi)(2164) · drawfag(2144)
- tsukudani_(coke-buta)(2135) · kanikama(2107) · koyama_shigeru(2096)
- milkpanda(2093) · ueyama_michirou(2077) · shino_(ponjiyuusu)(2072)
- neocoill(2068) · takafumi(2057) · tsunako(2018)

### C 档 · 1500–2000 张（半稳，风格辨识度高但权重偏弱，建议 1.2 起）84 个

- sincos(1988) · belko(1975) · gomashio_(goma_feet)(1964)
- taisa_(kari)(1963) · tsuda_nanafushi(1962) · izumi_tsubasu(1960)
- agawa_ryou(1956) · hana_kazari(1943) · sayori_(neko_works)(1925)
- konoshige_(ryuun)(1924) · wa_(genryusui)(1898) · null_(nyanpyoun)(1898)
- kotorai(1896) · toosaka_asagi(1888) · ginhaha(1888)
- sumiyao_(amam)(1884) · mattaku_mousuke(1874) · saiguchi_otoufu(1872)
- mizumizuni(1868) · yamamoto_souichirou(1836) · echo_(circa)(1833)
- anti_(untea9)(1830) · lolita_channel(1829) · yuuji_(and)(1822)
- kitsunerider(1822) · mochi_au_lait(1812) · enkyo_yuuichirou(1805)
- beni_shake(1804) · miyo_(ranthath)(1785) · horosuke(1784)
- yuuhagi_(amaretto-no-natsu)(1780) · tomose_shunsaku(1778) · mizuki_makoto(1775)
- nekotoufu(1774) · fujima_takuya(1752) · haruhisky(1751)
- zen_(kamuro)(1741) · minami_(colorful_palette)(1737) · fumihiko_(fu_mihi_ko)(1724)
- kashikaze(1709) · takeuchi_takashi(1687) · gonzarez(1681)
- gweda(1678) · clearite(1671) · yd_(orange_maru)(1667)
- ishikei(1656) · diva_(hyxpk)(1652) · ayu_(mog)(1649)
- yuureidoushi_(yuurei6214)(1646) · shiromanta(1640) · rappa_(rappaya)(1626)
- creayus(1623) · imu_sanjo(1621) · matsuryuu(1602)
- ichikawa_feesu(1597) · shimazaki_mujirushi(1595) · kasumi_(skchkko)(1588)
- mery_(yangmalgage)(1587) · tukiwani(1586) · merunyaa(1585)
- kaamin_(mariarose753)(1577) · oouso(1576) · chanta_(ayatakaoisii)(1564)
- ha_akabouzu(1560) · aaaa_(quad-a)(1555) · shirosato(1552)
- hinghoi(1550) · goma_(gomasamune)(1540) · nikorashi-ka(1536)
- kamille_(vcx68)(1529) · pageratta(1525) · as109(1525)
- asanagi(1519) · ohisashiburi(1517) · torotei(1516)
- ebi_193(1514) · jako_(jakoo21)(1513) · cle_masahiro(1512)
- koruri(1511) · yukito_(dreamrider)(1509) · hizaka(1509)
- ilya_kuvshinov(1508) · aldehyde(1507) · butcha-u(1503)

## 四、明天的实验矩阵（一次 6 张就能判定）

同一角色、同一构图、同一种子，只改画师段：

| # | 画师段 | 目的 |
|---|---|---|
| 1 | 无 | 基线 |
| 2 | `ebifurya` | 单 tag 是否可见 |
| 3 | `(ebifurya:1.2)` | 单 tag + 权重 |
| 4 | `ebifurya, hammer_(sunset_beach), tony_taka` | 三连（同厚涂系） |
| 5 | `(ebifurya:1.15), (tony_taka:1.1), impasto` | 三连 + 风格落点 |
| 6 | 反向加 `(ebifurya:1.2)` | 验证反向是否真的推开 |

判定标准：**看线条粗细、上色块的边缘、眼睛高光的形状**这三处，不要看整体「像不像」。

## 五、备注

- 本清单只收 danbooru 真实存在的 artist tag，可直接复制进提示词，不用改写法。
- 带括号的名字（如 `hammer_(sunset_beach)`、`kouji_(campus_life)`）整段照抄，括号是名字的一部分。
- 想要更全的分档：`python _setup/artist_rank.py 200`（前 200）/ `python _setup/artist_rank.py 500`。
- 校验任意 tag 是否存在：`python _setup/check_artist_tags.py`（改里面的 CAND 列表）。
