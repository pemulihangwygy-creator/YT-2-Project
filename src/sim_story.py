from .story import Scene


SOURCE_KORLANTAS = 'https://korlantas.polri.go.id/2026-11-04-korlantas-polri-tegaskan-informasi-pembuatan-sim-gratis-2026-hoaks/'
SOURCE_ANTARA = 'https://www.antaranews.com/berita/5835651/hoaks-program-pembuatan-sim-gratis-pada-november-2026'
SOURCE_LOCAL = 'https://korlantas.polri.go.id/2026-08-06-hut-ke-81-ri-satlantas-pasuruan-kota-beri-layanan-sim-c-gratis-khusus-bernama-agus-dan-lahir-agustus/'

SCENES = (
    Scene(
        '01.mp3', ('KLAIM VIRAL', 'SIM GRATIS SEUMUR HIDUP?'), 1,
        'Bikin SIM gratis, bahkan berlaku seumur hidup? Eits, jangan buru-buru percaya!',
        ('Bikin SIM gratis,', 'bahkan berlaku seumur hidup?', 'Eits, jangan buru-buru percaya!'),
        'claim',
    ),
    Scene(
        '02.mp3', ('DIBANTAH', 'KORLANTAS POLRI'), 0,
        'Kabar yang viral di media sosial itu dibantah Korlantas Polri. '
        'Unggahan tersebut bukan pengumuman resmi.',
        ('Kabar yang viral', 'di media sosial itu', 'dibantah Korlantas Polri.',
         'Unggahan tersebut', 'bukan pengumuman resmi.'),
        'verdict',
    ),
    Scene(
        '03.mp3', ('MASA BERLAKU SIM', 'LIMA TAHUN'), 1,
        'Faktanya, SIM berlaku lima tahun dan bisa diperpanjang. '
        'Biaya serta prosedurnya mengikuti ketentuan yang berlaku.',
        ('Faktanya, SIM berlaku', 'lima tahun', 'dan bisa diperpanjang.',
         'Biaya serta prosedurnya', 'mengikuti ketentuan yang berlaku.'),
        'validity',
    ),
    Scene(
        '04.mp3', ('WASPADA TAUTAN', 'MENCURIGAKAN'), 1,
        'Hati-hati kalau ada tautan mencurigakan yang meminta data pribadi, '
        'foto identitas, atau kode OTP!',
        ('Hati-hati kalau ada', 'tautan mencurigakan', 'yang meminta data pribadi,',
         'foto identitas,', 'atau kode OTP!'),
        'phishing',
    ),
    Scene(
        '05.mp3', ('PROGRAM KHUSUS?', 'CEK KANAL RESMI'), 1,
        'Program khusus di daerah bisa saja ada. Tapi cek tanggal dan syaratnya '
        'langsung lewat kanal resmi kepolisian.',
        ('Program khusus di daerah', 'bisa saja ada.', 'Tapi cek tanggal dan syaratnya',
         'langsung lewat kanal resmi kepolisian.'),
        'verify',
    ),
    Scene(
        '06.mp3', ('JANGAN BAGIKAN OTP', 'BAGIKAN FAKTANYA'), 1,
        'Jangan bagikan kode OTP, dan jangan transfer ke rekening yang belum jelas. '
        'Bagikan faktanya, biar temanmu aman!',
        ('Jangan bagikan kode OTP,', 'dan jangan transfer', 'ke rekening yang belum jelas.',
         'Bagikan faktanya,', 'biar temanmu aman!'),
        'protect',
    ),
)
