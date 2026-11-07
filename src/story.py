from dataclasses import dataclass


@dataclass(frozen=True)
class Scene:
    audio: str
    title: tuple[str, ...]
    highlight: int
    narration: str
    captions: tuple[str, ...]
    visual: str


SCENES = (
    Scene(
        '01.mp3', ('MOBIL MATIK', 'BERHENTI,', 'MESIN TETAP HIDUP?'), 2,
        'Mobil matik bisa berhenti tanpa mesinnya mati. Tapi, begitu gas diinjak, '
        'mobil langsung melaju. Kok bisa? Rahasianya ada pada komponen ini: torque converter!',
        ('Mobil matik', 'bisa berhenti', 'tanpa mesinnya mati.', 'Tapi, begitu gas diinjak,',
         'mobil langsung melaju.', 'Kok bisa?', 'Rahasianya ada pada', 'komponen ini:',
         'torque converter!'), 'intro',
    ),
    Scene(
        '02.mp3', ('TENAGA PINDAH', 'LEWAT OLI'), 1,
        'Torque converter, atau torcon, adalah penghubung antara mesin dan transmisi. '
        'Uniknya, tenaga dikirim lewat aliran oli, bukan sekadar sambungan logam yang kaku.',
        ('Torque converter,', 'atau torcon,', 'adalah penghubung', 'antara mesin dan transmisi.',
         'Uniknya, tenaga dikirim', 'lewat aliran oli,', 'bukan sekadar sambungan',
         'logam yang kaku.'), 'connection',
    ),
    Scene(
        '03.mp3', ('TIGA KOMPONEN', 'PENTING'), 1,
        'Di dalamnya ada tiga pemain utama. Impeler berputar bersama mesin, '
        'turbin tersambung ke transmisi, dan stator mengatur arah aliran oli.',
        ('Di dalamnya ada', 'tiga pemain utama.', 'Impeler berputar', 'bersama mesin,',
         'turbin tersambung', 'ke transmisi,', 'dan stator mengatur',
         'arah aliran oli.'), 'parts',
    ),
    Scene(
        '04.mp3', ('OLI MEMBAWA', 'TENAGA'), 1,
        'Saat mesin menyala, impeler melempar oli ke arah turbin. Dorongan oli '
        'membuat turbin ikut berputar, lalu tenaga diteruskan ke roda melalui transmisi.',
        ('Saat mesin menyala,', 'impeler melempar oli', 'ke arah turbin.',
         'Dorongan oli membuat', 'turbin ikut berputar,', 'lalu tenaga diteruskan',
         'ke roda melalui transmisi.'), 'flow',
    ),
    Scene(
        '05.mp3', ('BERHENTI TANPA', 'MESIN MATI'), 1,
        'Ketika rem diinjak dan mobil berhenti, impeler masih berputar, tetapi turbin '
        'bisa diam. Karena ada selisih putaran, mesin tidak harus ikut mati.',
        ('Ketika rem diinjak', 'dan mobil berhenti,', 'impeler masih berputar,',
         'tetapi turbin bisa diam.', 'Karena ada selisih putaran,', 'mesin tidak harus',
         'ikut mati.'), 'idle',
    ),
    Scene(
        '06.mp3', ('STATOR MEMBANTU', 'MEMPERBESAR TORSI'), 1,
        'Saat mobil mulai bergerak, stator mengarahkan oli yang kembali. Pada kondisi '
        'tertentu, aliran ini membantu memperbesar torsi, sehingga tarikan awal terasa lebih kuat.',
        ('Saat mobil mulai bergerak,', 'stator mengarahkan', 'oli yang kembali.',
         'Pada kondisi tertentu,', 'aliran ini membantu', 'memperbesar torsi,',
         'sehingga tarikan awal', 'terasa lebih kuat.'), 'stator',
    ),
    Scene(
        '07.mp3', ('KOPLING PENGUNCI', 'KURANGI SELIP'), 1,
        'Begitu melaju lebih cepat, banyak mobil matik modern memakai kopling pengunci. '
        'Hubungan mesin dan transmisi jadi lebih langsung, sehingga selip berkurang '
        'dan tenaga lebih efisien.',
        ('Begitu melaju lebih cepat,', 'banyak mobil matik modern', 'memakai kopling pengunci.',
         'Hubungan mesin dan transmisi', 'jadi lebih langsung,', 'sehingga selip berkurang',
         'dan tenaga lebih efisien.'), 'lockup',
    ),
    Scene(
        '08.mp3', ('TENAGA MENGALIR,', 'MATIK MELAJU'), 1,
        'Jadi, torcon bukan cuma cakram logam. Di dalamnya ada kerja sama komponen '
        'dan aliran oli yang bikin mobil matik bergerak lebih halus. Menarik, kan?',
        ('Jadi, torcon bukan', 'cuma cakram logam.', 'Di dalamnya ada', 'kerja sama komponen',
         'dan aliran oli', 'yang bikin mobil matik', 'bergerak lebih halus.',
         'Menarik, kan?'), 'outro',
    ),
)
