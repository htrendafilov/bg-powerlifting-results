from datetime import date

# National meets from the federation calendars, the results page and the
# federation Facebook page. A meet with no links is shown as "Няма протокол".
# The April 2020 equipped round was announced and then cancelled, so it is omitted.
CATALOG = [
    {
        "slug": "2011-gorna-oryahovitsa-krag-1",
        "name": "1 кръг, силов трибой с екипировка",
        "start": date(2011, 4, 2),
        "end": date(2011, 4, 3),
        "city": "Горна Оряховица",
        "links": [
            (
                "Протокол – мъже",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/protokol-11.xls",
            ),
            (
                "Протокол – жени",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/protokol_women.xls",
            ),
        ],
    },
    {
        "slug": "2011-gorna-oryahovitsa-youth",
        "name": "Първенство за юноши и младежи, силов трибой с екипировка",
        "start": date(2011, 4, 30),
        "city": "Горна Оряховица",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/mladeji-kraino.xls",
            ),
        ],
    },
    {
        "slug": "2011-sofia-leg",
        "name": "2 кръг, вдигане от лег с екипировка",
        "start": date(2011, 5, 21),
        "city": "София",
        "links": [
            (
                "Протокол – жени",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/jeni-leg.xls",
            ),
            (
                "Протокол – мъже",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/maje-leg.xls",
            ),
        ],
    },
    {
        "slug": "2011-sofia-kupa",
        "name": "Купа България, класически силов трибой",
        "start": date(2011, 9, 24),
        "end": date(2011, 9, 25),
        "city": "София",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/PROTOKOL-KUPA-BG.xls",
            ),
        ],
    },
    {
        "slug": "2011-gorna-oryahovitsa-oktomvri",
        "name": "3 кръг, силов трибой с екипировка",
        "start": date(2011, 10, 8),
        "end": date(2011, 10, 9),
        "city": "Горна Оряховица",
        "links": [
            (
                "Протокол – мъже",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/протокол-трети-кръг.xls",
            ),
            (
                "Протокол – жени",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/протокол-жени-трети-краг.xls",
            ),
        ],
    },
    {
        "slug": "2012-gorna-oryahovitsa-krag-1",
        "name": "1 кръг, силов трибой с екипировка",
        "start": date(2012, 3, 17),
        "end": date(2012, 3, 18),
        "city": "Горна Оряховица",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/protokoli-1-krag.xls",
            ),
        ],
    },
    {
        "slug": "2012-dupnitsa-youth",
        "name": "Първенство за юноши и младежи, силов трибой с екипировка",
        "start": date(2012, 4, 28),
        "end": date(2012, 4, 29),
        "city": "Дупница",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/младежи-и-девойки1.xls",
            ),
        ],
    },
    {
        "slug": "2012-gorna-oryahovitsa-leg",
        "name": "2 кръг, вдигане от лег с и без екип",
        "start": date(2012, 5, 19),
        "end": date(2012, 5, 20),
        "city": "Горна Оряховица",
        "links": [
            (
                "Без екипировка",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/19.05-bez-ekip.xls",
            ),
            (
                "С екипировка",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/20.05-leg-s-ekip.xls",
            ),
        ],
    },
    {
        "slug": "2012-dupnitsa-kupa",
        "name": "Купа България, класически силов трибой",
        "start": date(2012, 9, 15),
        "end": date(2012, 9, 16),
        "city": "Дупница",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/Kupa_Bulgaria-maje-i-jeni-dupnica1.xls",
            ),
        ],
    },
    {
        "slug": "2012-haskovo-otborno",
        "name": "Отборно първенство, силов трибой с екипировка",
        "start": date(2012, 10, 7),
        "city": "Хасково",
        "links": [],
    },
    {
        "slug": "2013-gorna-oryahovitsa-krag-1",
        "name": "1 кръг, силов трибой с екипировка",
        "start": date(2013, 3, 23),
        "end": date(2013, 3, 24),
        "city": "Горна Оряховица",
        "links": [
            (
                "Протокол – мъже",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2014/08/24-03-2013-Gorna-Oryahovica.xls",
            ),
            (
                "Протокол – жени",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2014/08/23-03-2013-women.xls",
            ),
        ],
    },
    {
        "slug": "2013-aytos-youth",
        "name": "Първенство за юноши и младежи, силов трибой с екипировка",
        "start": date(2013, 3, 31),
        "city": "Айтос",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2013/04/31-03-2013-detailed_scoresheet.xls",
            ),
        ],
    },
    {
        "slug": "2013-dupnitsa-leg",
        "name": "2 кръг, вдигане от лег с и без екип",
        "start": date(2013, 6, 1),
        "city": "Дупница",
        "links": [
            (
                "Без екипировка",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2013/06/kraino-без-екип.xls",
            ),
            (
                "С екипировка",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2013/06/dupnica-ekipirovka.xls",
            ),
        ],
    },
    {
        "slug": "2013-varna-kupa",
        "name": "3 кръг, Купа България, класически силов трибой",
        "start": date(2013, 9, 14),
        "end": date(2013, 9, 15),
        "city": "Варна",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2013/09/3-КРЪГ.xls",
            ),
        ],
    },
    {
        "slug": "2014-gorna-oryahovitsa-krag-1",
        "name": "1 кръг, силов трибой с екипировка",
        "start": date(2014, 3, 8),
        "end": date(2014, 3, 9),
        "city": "Горна Оряховица",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2014/03/протокол-1-кръг.xlsx",
            ),
        ],
    },
    {
        "slug": "2014-sofia-leg",
        "name": "2 кръг, вдигане от лег с и без екип",
        "start": date(2014, 5, 30),
        "end": date(2014, 5, 31),
        "city": "София",
        "links": [
            (
                "Без екипировка",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2014/06/bez-ekip-2014.xls",
            ),
            (
                "С екипировка",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2014/06/s-ekip-2014.xls",
            ),
        ],
    },
    {
        "slug": "2014-dupnitsa-kupa",
        "name": "3 кръг, Купа България, класически силов трибой",
        "start": date(2014, 9, 13),
        "end": date(2014, 9, 14),
        "city": "Дупница",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2014/10/treti-krag-kraini1.xls",
            ),
        ],
    },
    {
        "slug": "2015-gorna-oryahovitsa-krag-1",
        "name": "1 кръг, силов трибой с екипировка",
        "start": date(2015, 4, 4),
        "end": date(2015, 4, 5),
        "city": "Горна Оряховица",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2015/04/Protokoli-Silov-Triboi-Republikansko-1-vi-Krug-2015.ods",
            ),
        ],
    },
    {
        "slug": "2015-haskovo-leg",
        "name": "2 кръг, вдигане от лег с и без екип, Купа „Антон Колев“",
        "start": date(2015, 6, 20),
        "city": "Хасково",
        "links": [
            (
                "Без екипировка",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2015/06/ДЛОШ-Кръг-2-Купа-Антон-Колев-2015-БЕЗ-ЕКИПИРОВКА.xlsx",
            ),
            (
                "С екипировка",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2015/06/ДЛОШ-Кръг-2-Купа-Антон-Колев-2015-ЕКИПИРОВКА.xlsx",
            ),
        ],
    },
    {
        "slug": "2015-dupnitsa-kupa",
        "name": "3 кръг, Купа България, класически силов трибой",
        "start": date(2015, 9, 19),
        "end": date(2015, 9, 20),
        "city": "Дупница",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2015/09/Protokoli-Dupnica-2015-Krug-III.xls",
            ),
        ],
    },
    {
        "slug": "2016-gorna-oryahovitsa-krag-1",
        "name": "1 кръг, силов трибой с екипировка",
        "start": date(2016, 4, 2),
        "end": date(2016, 4, 3),
        "city": "Горна Оряховица",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2010/08/protokol-1-krag-mms.xls",
            ),
        ],
    },
    {
        "slug": "2016-haskovo-leg",
        "name": "2 кръг, вдигане от лег с и без екип, Купа „Антон Колев“",
        "start": date(2016, 6, 18),
        "city": "Хасково",
        "links": [
            (
                "Без екипировка",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2016/06/2-krag-bez1.xls",
            ),
            (
                "С екипировка",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2016/06/2-krag-s-ekip.xls",
            ),
        ],
    },
    {
        "slug": "2016-kozloduy-krag-3",
        "name": "3 кръг, класически силов трибой, Купа „АЕЦ Козлодуй“",
        "start": date(2016, 9, 3),
        "end": date(2016, 9, 4),
        "city": "Козлодуй",
        "links": [],
    },
    {
        "slug": "2017-gorna-oryahovitsa-krag-1",
        "name": "1 кръг, силов трибой с екипировка",
        "start": date(2017, 3, 4),
        "end": date(2017, 3, 5),
        "city": "Горна Оряховица",
        "links": [
            (
                "Протокол – мъже",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2017/03/protokol-1-krag.xlsx",
            ),
            (
                "Протокол – жени",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2017/03/1-кръг-жени-03.2017г..xls",
            ),
            (
                "Юноши и младежи",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2017/03/unushi-mladeji1.xls",
            ),
            (
                "Ветерани",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2017/03/ветерани-03.2017г.1.xlsx",
            ),
        ],
    },
    {
        "slug": "2017-sofia-leg",
        "name": "2 кръг, вдигане от лег с и без екип",
        "start": date(2017, 6, 3),
        "city": "София",
        # Протокол с резултати не е публикуван; на сайта има само заявки и график.
        "links": [],
    },
    {
        "slug": "2017-haskovo-krag-3",
        "name": "3 кръг, класически силов трибой",
        "start": date(2017, 9, 9),
        "end": date(2017, 9, 10),
        "city": "Хасково",
        "links": [
            (
                "Мъже – всички възрасти",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2017/09/DLOSH-3-2017-Klasirane-Maje-wsichki-vuzrasti.pdf",
            ),
            (
                "Жени – всички възрасти",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2017/09/DLOSH-3-2017-Klasirane-Jeni-wsichki-vuzrasti.pdf",
            ),
            (
                "Юноши",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2017/09/DLOSH-3-2017-Klasirane-Maje-Unushi.pdf",
            ),
            (
                "Младежи",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2017/09/DLOSH-3-2017-Klasirane-Maje-Mladeji.pdf",
            ),
            (
                "Ветерани",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2017/09/DLOSH-3-2017-Klasirane-Maje-Veterani.pdf",
            ),
            (
                "Жени по възраст",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2017/09/DLOSH-3-2017-Klasirane-Jeni-spored-vuzrastta.pdf",
            ),
        ],
    },
    {
        "slug": "2018-sofia-ekip",
        "name": "1 кръг, силов трибой с екипировка",
        "start": date(2018, 3, 31),
        "end": date(2018, 4, 1),
        "city": "София",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/%d0%bf%d1%80%d0%be%d1%82%d0%be%d0%ba%d0%be%d0%bb%d0%b8-%d0%be%d1%82-%d0%bf%d1%8a%d1%80%d0%b2%d0%b8-%d0%ba%d1%80%d1%8a%d0%b3-%d0%bd%d0%b0-%d1%80%d0%b5%d0%bf%d1%83%d0%b1%d0%bb%d0%b8%d0%ba%d0%b0%d0%bd/",
            ),
        ],
    },
    {
        "slug": "2018-dupnitsa-leg",
        "name": "2 кръг, вдигане от лег с и без екип",
        "start": date(2018, 6, 9),
        "city": "Дупница",
        "links": [],
    },
    {
        "slug": "2018-sofia-classic",
        "name": "3 кръг, класически силов трибой",
        "start": date(2018, 9, 22),
        "end": date(2018, 9, 23),
        "city": "София",
        "links": [],
    },
    {
        "slug": "2019-sofia-ekip",
        "name": "1 кръг, силов трибой с екипировка",
        "start": date(2019, 3, 23),
        "end": date(2019, 3, 24),
        "city": "София",
        "links": [],
    },
    {
        "slug": "2019-varna-leg",
        "name": "2 кръг, вдигане от лег с и без екип",
        "start": date(2019, 6, 1),
        "city": "Варна",
        "links": [],
    },
    {
        "slug": "2019-haskovo-classic",
        "name": "3 кръг, класически силов трибой",
        "start": date(2019, 9, 14),
        "end": date(2019, 9, 15),
        "city": "Хасково",
        "links": [],
    },
    {
        "slug": "2020-dupnitsa-leg",
        "name": "2 кръг, вдигане от лег с и без екип",
        "start": date(2020, 8, 23),
        "city": "Дупница",
        "links": [],
    },
    {
        "slug": "2020-sofia-sbd",
        "name": "Силов трибой с и без екип",
        "start": date(2020, 9, 6),
        "end": date(2020, 9, 7),
        "city": "София",
        "links": [],
    },
    {
        "slug": "2021-dupnitsa-krag-1",
        "name": "1 кръг, класически силов трибой",
        "start": date(2021, 6, 5),
        "end": date(2021, 6, 6),
        "city": "Дупница",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2021/06/Протоколи-1-кръг-Дупница-05-06.06.2021.zip",
            )
        ],
    },
    {
        "slug": "2021-dupnitsa-leg",
        "name": "2 кръг, вдигане от лег с и без екип",
        "start": date(2021, 7, 4),
        "city": "Дупница",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2021/07/Протоколи-лег-Дупница-04.07.2021.zip",
            )
        ],
    },
    {
        "slug": "2021-haskovo-krag-3",
        "name": "3 кръг, класически силов трибой",
        "start": date(2021, 9, 18),
        "end": date(2021, 9, 19),
        "city": "Хасково",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2021/09/Протоколи-3кръг-Хасково-18-19.09.2021г.zip",
            )
        ],
    },
    {
        "slug": "2022-haskovo-leg",
        "name": "1 кръг, вдигане от лег с и без екип",
        "start": date(2022, 5, 28),
        "end": date(2022, 5, 29),
        "city": "Хасково",
        "links": [
            (
                "Протокол",
                "https://docs.google.com/spreadsheets/d/10gvYi5WYF1CnR1aJd6b5zDW1n9EBtonq/edit",
            )
        ],
    },
    {
        "slug": "2022-haskovo-kupa-anton-kolev",
        "name": "Купа „Антон Колев“",
        "start": date(2022, 6, 18),
        "end": date(2022, 6, 19),
        "city": "Хасково",
        "links": [],
    },
    {
        "slug": "2022-dupnitsa-ekip",
        "name": "2 кръг, силов трибой с екип",
        "start": date(2022, 7, 2),
        "end": date(2022, 7, 3),
        "city": "Дупница",
        "links": [
            (
                "Протокол",
                "https://docs.google.com/spreadsheets/d/1Bq5WAwqGw0ioyL4vdpyS-NkGi__-k73x/edit",
            )
        ],
    },
    {
        "slug": "2022-gorna-oryahovitsa-classic",
        "name": "3 кръг, силов трибой без екип",
        "start": date(2022, 9, 10),
        "end": date(2022, 9, 11),
        "city": "Горна Оряховица",
        # Продълженото от федерацията тук сочи към протокола на Дупница 2023.
        "links": [],
    },
    {
        "slug": "2023-kardzhali-ekip",
        "name": "1 кръг, силов трибой с екип",
        "start": date(2023, 4, 8),
        "end": date(2023, 4, 9),
        "city": "Кърджали",
        "links": [
            (
                "Протокол",
                "https://docs.google.com/spreadsheets/d/1VDGW2S9F1hqDbuowaguC9Wxt2KErtXd8/edit",
            )
        ],
    },
    {
        "slug": "2023-sofia-leg",
        "name": "2 кръг, вдигане от лег с и без екип",
        "start": date(2023, 5, 27),
        "end": date(2023, 5, 28),
        "city": "София",
        "links": [
            (
                "Жени",
                "https://drive.google.com/file/d/1RujTs2NCKV844EcJC_bqtqqT66srOcbO/view",
            ),
            (
                "Мъже без екип",
                "https://drive.google.com/file/d/1MdK-klTPTdNSAXs95aBVk0P-3cCXIkRp/view",
            ),
            (
                "Мъже с екип",
                "https://drive.google.com/file/d/1z4qo6JI4sW9KSHdXweDFo7dwKpwYWAIk/view",
            ),
        ],
    },
    {
        "slug": "2023-dupnitsa-classic",
        "name": "3 кръг, класически силов трибой",
        "start": date(2023, 7, 1),
        "end": date(2023, 7, 2),
        "city": "Дупница",
        # Намерен през страницата на федерацията във Facebook; на сайта им
        # е закачен по погрешка за Горна Оряховица 2022.
        "links": [
            (
                "Протокол",
                "https://drive.google.com/file/d/1Vaa9h-kUtZiJ6lprq7Vamv_BfW7ZJfK_/view",
            )
        ],
    },
    {
        "slug": "2023-haskovo-leg",
        "name": "4 кръг, вдигане от лег с и без екип",
        "start": date(2023, 10, 7),
        "city": "Хасково",
        "links": [],
    },
    {
        "slug": "2023-sofia-deadlift",
        "name": "Национален шампионат по мъртва тяга",
        "start": date(2023, 11, 26),
        "city": "София",
        "links": [
            (
                "Протокол",
                "https://docs.google.com/spreadsheets/d/1BQY0kWUdx__ifToZ05DZMgpytoyo5nL6/edit",
            )
        ],
    },
    {
        "slug": "2024-pernik-ekip",
        "name": "Екипировъчен силов трибой",
        "start": date(2024, 4, 13),
        "end": date(2024, 4, 14),
        "city": "Перник",
        "links": [
            (
                "Протокол, събота",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2024/04/Championships-IPF-GL-example-1-krug-protokol-Saturday-1.pdf",
            ),
            (
                "Протокол, неделя",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2024/04/Championships-IPF-GL-example-1-krug-protokol-Sunday-1.pdf",
            ),
        ],
    },
    {
        "slug": "2024-sofia-leg-may",
        "name": "Вдигане от лег с и без екип",
        "start": date(2024, 5, 25),
        "city": "София",
        "links": [],
    },
    {
        "slug": "2024-dupnitsa-leg",
        "name": "Вдигане от лег с и без екип",
        "start": date(2024, 9, 22),
        "city": "Дупница",
        "links": [
            (
                "Протокол",
                "https://docs.google.com/spreadsheets/d/1Nprtrv3Ru9MWLHr9BT1ahykV3EAwb0w5/edit",
            )
        ],
    },
    {
        "slug": "2024-sofia-classic",
        "name": "Класически силов трибой",
        "start": date(2024, 11, 16),
        "end": date(2024, 11, 17),
        "city": "София",
        "links": [
            (
                "Протокол",
                "https://docs.google.com/spreadsheets/d/1gXFJMhrhIB4bdvgULSkjz-Q55xNN3nz32yulxQUzjGE/edit",
            )
        ],
    },
    {
        "slug": "2025-gorna-oryahovitsa-ekip",
        "name": "1 кръг, екипировъчен силов трибой",
        "start": date(2025, 4, 11),
        "end": date(2025, 4, 13),
        "city": "Горна Оряховица",
        "links": [
            (
                "Протокол",
                "https://docs.google.com/spreadsheets/d/1VW34aJkBUoUMFOD30RorNz0FcfMj4BD_nm1P13PZRIU/edit",
            )
        ],
    },
    {
        "slug": "2025-varna-leg",
        "name": "2 кръг, вдигане от лег с и без екип",
        "start": date(2025, 5, 31),
        "end": date(2025, 6, 1),
        "city": "Варна",
        "links": [
            (
                "Протокол",
                "https://docs.google.com/spreadsheets/d/1oyl42ZkyxzKMtDoTYsVZEqsepb7jn-B7/edit",
            )
        ],
    },
    {
        "slug": "2025-kardzhali-classic",
        "name": "3 кръг, класически силов трибой",
        "start": date(2025, 9, 19),
        "end": date(2025, 9, 21),
        "city": "Кърджали",
        "links": [
            (
                "Протокол",
                "https://docs.google.com/spreadsheets/d/17bTU3jdzzlnKAeMmu-gejecxNe0Khd2bPhbN_aH5zCE/edit",
            )
        ],
    },
    {
        "slug": "2025-dupnitsa-youth",
        "name": "Класически силов трибой за юноши и младежи",
        "start": date(2025, 12, 6),
        "city": "Дупница",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2025/12/06.12.2025D0B3.20D0B3D180.D094D183D0BFD0BDD0B8D186D0B0.xlsx",
            )
        ],
    },
    {
        "slug": "2026-svishtov-ekip",
        "name": "Екипировъчен силов трибой",
        "start": date(2026, 4, 3),
        "end": date(2026, 4, 5),
        "city": "Свищов",
        "links": [
            (
                "Протокол",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2026/04/Републиканско-по-силов-трибой-екип-Свищов-април-2026-1.xlsx",
            )
        ],
    },
    {
        "slug": "2026-sofia-leg",
        "name": "Вдигане от лег с и без екип",
        "start": date(2026, 5, 30),
        "end": date(2026, 5, 31),
        "city": "София",
        "links": [
            (
                "Мъже без екип",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2026/06/M_v2_0e7237ce-0960-4985-93be-7f54f87e8da4.xlsx",
            ),
            (
                "Мъже с екип",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2026/06/M-Eq_v2_6b841349-0e94-4395-829b-78d941fe0845.xlsx",
            ),
            (
                "Жени",
                "https://powerlifting-bg.com/bpl/wp-content/uploads/2026/06/W_v2_c59cf908-d149-4aa9-9465-45978b3b291b.xlsx",
            ),
        ],
    },
    {
        "slug": "2026-gorna-oryahovitsa-classic",
        "name": "Класически силов трибой",
        "start": date(2026, 9, 19),
        "end": date(2026, 9, 20),
        "city": "Горна Оряховица",
        "links": [
            (
                "Протокол",
                "https://docs.google.com/spreadsheets/d/1gkv44GR7_JSGAnIwt8rN7z8LFcRKNnffvHl6HR880U4/edit",
            )
        ],
    },
    {
        "slug": "2026-sofia-youth",
        "name": "Класически силов трибой за юноши и младежи",
        "start": date(2026, 11, 1),
        "city": "София",
        "links": [],
    },
    {
        "slug": "2026-dupnitsa-kupa",
        "name": "Купа България, вдигане от лег",
        "start": date(2026, 12, 6),
        "city": "Дупница",
        "links": [],
    },
]
