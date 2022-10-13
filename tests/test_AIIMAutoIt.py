import unittest
from unittest import mock
import pandas as pd
from AIIMAutoIt import AIIMAutoIt
from ConfigFiles import Infraction


def _get_text_mock(*args, **kwargs):
    if args[1] == '[CLASS:ThunderRT6ComboBox; INSTANCE:6]':
        return '1'
    elif args[1] == '[CLASS:ThunderRT6TextBox; INSTANCE:35]':
        return '1.111.111-1'
    elif args[0] == '[CLASS:#32770; TITLE:AIIM2003]' and args[1] == '[CLASS:Static; INSTANCE:2]':
        return 'DAVB inconsistente!'
    return 'Qualquer coisa'


class AIIMAutoItTest(unittest.TestCase):
    @mock.patch('AIIMAutoIt.time')
    @mock.patch('AIIMAutoIt.autoit')
    def test_fill_ddf_for_all_default_infractions(self, mock_autoit, mock_time):
        aiim2003 = AIIMAutoIt()
        mock_autoit.control_get_text.side_effect = _get_text_mock
        ddf_one_for_all = pd.DataFrame(columns=['referencia', 'valor', 'valor_basico', 'dci', 'dij',
                                                'dcm', 'davb', 'dia_seguinte', 'vencimento',
                                                'Livros', 'Meses', 'atraso', 'documentos', ],
                                       data=[['01/01/2022', '100,20', '50,00', '01/01/2022', '01/01/2022',
                                              '31/01/2022', '31/12/2022', '02/01/2022', '20/02/2022',
                                              '1', '2', '150', '1']])
        for infraction in Infraction.all_default_infractions():
            aiim2003.preenche_ddf('1.111.111-1', 1, 1,
                                  {'infracao': infraction, 'ddf': ddf_one_for_all})
