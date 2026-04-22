UPLOAD_FOLDER = 'static'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

PAY_TYPE_ID = {
    'four_qtr' : 1,
    'single' : 2,
    'every_score' : 3,
    'touch' : 4,
    'ten_man' : 5,
    'satellite' : 6,
    'ten_man_final_reverse': 7,
    'every_minute': 8,
    'ten_man_final_half': 9
}

BOX_TYPE_ID = {
    'dailybox' : 1,
    'custom' : 2,
    'nutcracker' : 3,
    'private' : 4
}

EMOJIS = {
    'thumbs_up': '\uD83D\uDC4D'.encode('utf-16', 'surrogatepass').decode('utf-16'),
    'thumbs_down': '\uD83D\uDC4E'.encode('utf-16', 'surrogatepass').decode('utf-16'),
    'middle_finger': '\uD83D\uDD95'.encode('utf-16', 'surrogatepass').decode('utf-16'),
    'check': '\u2714',
    'ex': '\u274c',
    'crown': '\uD83C\uDFC6'.encode('utf-16', 'surrogatepass').decode('utf-16')
}
