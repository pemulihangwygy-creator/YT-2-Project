from dataclasses import dataclass


@dataclass(frozen=True)
class Scene:
    audio: str
    title: tuple[str, ...]
    highlight: int
    captions: tuple[str, ...]
    visual: str


SCENES = (
    Scene(
        '01.mp3', ('KOK MOBIL MATIK', 'BISA BERHENTI', 'TANPA MATI?'), 2,
        ('Kenapa mobil matik', 'bisa berhenti', 'tanpa mesinnya mati,',
         'lalu langsung bergerak', 'saat gas diinjak?', 'Jawabannya ada di',
         'komponen bundar bernama', 'torque converter.'), 'intro',
    ),
    Scene(
        '02.mp3', ('TENAGA PINDAH', 'LEWAT OLI'), 1,
        ('Torque converter,', 'atau torcon,', 'menghubungkan mesin dan transmisi',
         'lewat aliran oli.', 'Jadi, tenaga tidak selalu', 'berpindah melalui',
         'sambungan mekanis yang kaku.'), 'connection',
    ),
    Scene(
        '03.mp3', ('TIGA KOMPONEN', 'UTAMA'), 1,
        ('Di dalamnya ada', 'tiga bagian utama:', 'impeler yang diputar mesin,',
         'turbin yang terhubung', 'ke transmisi,', 'dan stator yang berada',
         'di antara keduanya.'), 'parts',
    ),
    Scene(
        '04.mp3', ('OLI MEMBAWA', 'TENAGA'), 1,
        ('Saat mesin hidup,', 'impeler berputar', 'dan mendorong oli',
         'ke arah turbin.', 'Aliran ini membuat turbin', 'ikut berputar',
         'dan meneruskan tenaga', 'ke transmisi.'), 'flow',
    ),
    Scene(
        '05.mp3', ('BERHENTI TANPA', 'MESIN MATI'), 1,
        ('Ketika mobil berhenti', 'dengan rem diinjak,', 'impeler tetap berputar',
         'sementara turbin bisa diam.', 'Selisih putaran itulah',
         'yang membantu mesin', 'tetap menyala.'), 'idle',
    ),
    Scene(
        '06.mp3', ('STATOR MEMBANTU', 'MEMPERBESAR TORSI'), 1,
        ('Saat mulai bergerak,', 'stator mengarahkan kembali', 'aliran oli.',
         'Dalam kondisi tertentu,', 'ini memperbesar torsi',
         'dan membantu tarikan awal', 'menjadi lebih kuat.'), 'stator',
    ),
    Scene(
        '07.mp3', ('KOPLING PENGUNCI', 'KURANGI SELIP'), 1,
        ('Ketika kecepatan', 'sudah cukup tinggi,', 'banyak torcon modern',
         'memakai kopling pengunci.', 'Bagian ini mengurangi selip,',
         'sehingga penyaluran tenaga', 'jadi lebih efisien.'), 'lockup',
    ),
    Scene(
        '08.mp3', ('PERPINDAHAN TENAGA', 'LEBIH HALUS'), 1,
        ('Jadi, torcon bukan', 'sekadar cakram logam.', 'Komponen ini',
         'memanfaatkan oli', 'untuk meneruskan tenaga', 'dengan halus.',
         'Sekarang kamu tahu, kan,', 'bagaimana mobil matik',
         'bisa melaju?'), 'outro',
    ),
)
