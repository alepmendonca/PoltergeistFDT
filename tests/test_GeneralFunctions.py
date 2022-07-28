from datetime import datetime
from datetime import date

from unittest import TestCase

import GeneralFunctions


class GeneralFunctionsTest(TestCase):
    def test_last_day_of_month_happyday(self):
        self.assertEqual(date(2021, 1, 31),
                         GeneralFunctions.last_day_of_month(date(2021, 1, 1)))
        self.assertEqual(date(2021, 2, 28),
                         GeneralFunctions.last_day_of_month(date(2021, 2, 1)))
        self.assertEqual(date(2021, 12, 31),
                         GeneralFunctions.last_day_of_month(date(2021, 12, 31)))
        self.assertEqual(date(2024, 2, 29),
                         GeneralFunctions.last_day_of_month(date(2024, 2, 15)))

    def test_first_day_of_month_before(self):
        self.assertEqual(date(2020, 1, 1),
                         GeneralFunctions.first_day_of_month_before(datetime(2020, 2, 15)),
                         )
        self.assertEqual(date(2020, 6, 1),
                         GeneralFunctions.first_day_of_month_before(date(2020, 7, 30)),
                         )

    def test_periodos_prettyprint_happyday(self):
        self.assertEqual('o período de 2020 a 2022',
                         GeneralFunctions.periodos_prettyprint(
                             [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)],
                             freq='Y'))
        self.assertEqual('os períodos de 2020, 2023 e 2025',
                         GeneralFunctions.periodos_prettyprint(
                             [datetime(2020, 3, 1), datetime(2023, 1, 1), datetime(2025, 12, 1)],
                             freq='Y'))
        self.assertEqual('o período de janeiro a março de 2020',
                         GeneralFunctions.periodos_prettyprint(
                             [datetime(2020, 1, 1), datetime(2020, 2, 1), datetime(2020, 3, 1)]
                         ))
        self.assertEqual('os períodos de janeiro de 2020, janeiro de 2021 e janeiro de 2022',
                         GeneralFunctions.periodos_prettyprint(
                             [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)],
                             freq='M'))
        self.assertEqual('os períodos de maio, julho e dezembro de 2020',
                         GeneralFunctions.periodos_prettyprint(
                             [datetime(2020, 5, 1), datetime(2020, 7, 1), datetime(2020, 12, 1)]))
        self.assertEqual('o período de fevereiro de 2020',
                         GeneralFunctions.periodos_prettyprint([datetime(2020, 2, 1)]))
        self.assertEqual('os períodos de janeiro, fevereiro e abril a junho de 2020 e janeiro e fevereiro de 2021',
                         GeneralFunctions.periodos_prettyprint(
                             [datetime(2020, 1, 1), datetime(2020, 2, 1), datetime(2020, 4, 1),
                              datetime(2020, 5, 1), datetime(2020, 6, 1), datetime(2021, 1, 1), datetime(2021, 2, 1)]))
        self.assertEqual('os períodos de janeiro a março de 2020, fevereiro a maio e julho de 2021 e outubro a '
                         'dezembro de 2022',
                         GeneralFunctions.periodos_prettyprint(
                             [datetime(2020, 1, 1), datetime(2020, 2, 1), datetime(2020, 3, 1),
                              datetime(2021, 2, 1), datetime(2021, 3, 1), datetime(2021, 4, 1), datetime(2021, 5, 1),
                              datetime(2021, 7, 1), datetime(2022, 10, 1), datetime(2022, 11, 1), datetime(2022, 12, 1)]))
        self.assertEqual('os períodos de dezembro de 2021 e janeiro e fevereiro de 2022',
                         GeneralFunctions.periodos_prettyprint(
                             [datetime(2021, 12, 1), datetime(2022, 1, 1), datetime(2022, 2, 1)]
                         ))
        self.assertEqual('os períodos de janeiro e dezembro de 2021 e janeiro e fevereiro de 2022',
                         GeneralFunctions.periodos_prettyprint(
                             [datetime(2021, 1, 1), datetime(2021, 12, 1), datetime(2022, 1, 1), datetime(2022, 2, 1)]
                         ))

    def test_default_business_name(self):
        self.assertEqual('Florinda', GeneralFunctions.get_default_name_for_business('RESTAURANTE FLORINDA'))
        self.assertEqual('Cangao', GeneralFunctions.get_default_name_for_business('CANGAÇO'))
        self.assertEqual('DRPimpolho', GeneralFunctions.get_default_name_for_business('DR PIMPOLHO'))