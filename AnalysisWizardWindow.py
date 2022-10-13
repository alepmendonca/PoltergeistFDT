import json
import PySimpleGUI as sg

import GUIFunctions
import GeneralFunctions
from ConfigFiles import Infraction, AiimProof, Analysis


class AnalysisWizardWindow(sg.Window):
    window = None
    infracao: Infraction
    analysis_dict = {}
    default_size = (800, 32 * len(AiimProof.proof_types.keys()) + 50)

    def has_infraction(self) -> bool:
        return self.analysis_dict.get('infracoes') \
               and ((isinstance(self.analysis_dict['infracoes'], list)
                     and self.infracao.filename in self.analysis_dict['infracoes'])
                    or
                    (isinstance(self.analysis_dict['infracoes'], dict)
                     and self.infracao.filename in self.analysis_dict['infracoes'].keys()))

    def has_overriden_field(self, field: str) -> bool:
        return self.has_infraction() and isinstance(self.analysis_dict['infracoes'], dict) \
               and field in self.analysis_dict['infracoes'][self.infracao.filename].keys()

    def has_overriden_proof(self, proof_type: str) -> bool:
        return self.has_overriden_field('provas') \
               and proof_type in [p['tipo'] for p in self.analysis_dict['infracoes'][self.infracao.filename]['provas']]

    def has_default_proof(self, proof_type: str) -> bool:
        return not self.has_overriden_field('provas') \
               and proof_type in [p.tipo for p in self.infracao.provas]

    def proof_description(self, proof_type: str) -> str:
        if self.has_overriden_proof(proof_type):
            descricoes = [p['descricao'] for p in self.analysis_dict['infracoes'][self.infracao.filename]['provas']
                          if p['tipo'] == proof_type]
            return descricoes[0] if descricoes else ''
        if self.has_default_proof(proof_type):
            descricoes = [p.descricao for p in self.infracao.provas if p.tipo == proof_type]
            return descricoes[0] if descricoes else ''
        return ''

    def _change_proof_list(self, selected_item, lista):
        self['-NEW-ANALYSIS-PROOF-LIST-'].update(lista)
        self['-NEW-ANALYSIS-PROOF-LIST-'].set_value([selected_item])
        if selected_item:
            self['-NEW-ANALYSIS-PROOF-UP-'].update(disabled=
                                                   self['-NEW-ANALYSIS-PROOF-LIST-'].get_list_values()[0] == selected_item)
            self['-NEW-ANALYSIS-PROOF-DOWN-'].update(disabled=
                                                     self['-NEW-ANALYSIS-PROOF-LIST-'].get_list_values()[
                                                         -1] == selected_item)
        else:
            self['-NEW-ANALYSIS-PROOF-UP-'].update(disabled=True)
            self['-NEW-ANALYSIS-PROOF-DOWN-'].update(disabled=True)

    def __init__(self, passo=1):
        super().__init__('Nova Análise')
        if passo == 1:
            self.__create_window([
                [[sg.Text('Nome da nova análise:     '),
                  sg.InputText(key='-NEW-ANALYSIS-NAME-', default_text=self.analysis_dict.get('verificacao'),
                               expand_x=True)],
                 [sg.Text('Infração:                 '),
                  sg.Combo(values=Infraction.all_default_infractions(), key='-NEW-ANALYSIS-INFRACTION-',
                           default_value=Infraction.get_by_name(list(self.analysis_dict['infracoes'].keys())[0])
                           if self.analysis_dict.get('infracoes') else None,
                           readonly=True)],
                 [sg.Text('Consulta SQL:             '),
                  sg.Multiline(
                      default_text=self.analysis_dict['consulta'] if self.analysis_dict.get('consulta') else '',
                      size=(300, 15),
                      expand_x=True, expand_y=True,
                      key='-NEW-ANALYSIS-SQL-', auto_size_text=True)],
                 [sg.Text('Nome Padrão para Planilha:'),
                  sg.InputText(
                      default_text=self.analysis_dict['planilha_nome'] if self.analysis_dict.get(
                          'planilha_nome') else '',
                      key='-NEW-ANALYSIS-SHEET-', expand_x=True)],
                 [sg.Push(),
                  sg.Button('Próximo', key='-NEW-ANALYSIS-NEXT2-'),
                  sg.Push()]],
            ])
        elif passo == 2:
            self.__create_window([
                [[sg.Checkbox('Deve mandar notificação', key='-NEW-ANALYSIS-NOTIFICATION-CHECK-',
                              default=self.analysis_dict.get('notificacao'),
                              enable_events=True)],
                 [sg.Text('Título da Notificação:  '),
                  sg.InputText(key='-NEW-ANALYSIS-NOTIFICATION-TITLE-',
                               default_text=self.analysis_dict.get('notificacao', {}).get('titulo', ''),
                               disabled=not self.analysis_dict.get('notificacao'))],
                 [sg.Text('Corpo da Notificação:  '),
                  sg.Multiline(default_text=self.analysis_dict.get('notificacao', {}).get('corpo', ''),
                               size=(300, 15),
                               expand_x=True, expand_y=True,
                               key='-NEW-ANALYSIS-NOTIFICATION-BODY-', auto_size_text=True,
                               disabled=not self.analysis_dict.get('notificacao'))],
                 [sg.Text('Nome do Anexo:         '),
                  sg.InputText(key='-NEW-ANALYSIS-NOTIFICATION-ATTACHMENT-',
                               default_text=self.analysis_dict.get('notificacao', {}).get('anexo', ''),
                               disabled=not self.analysis_dict.get('notificacao'))],
                 [sg.Push(),
                  sg.Button('Anterior', key='-NEW-ANALYSIS-BACK1-'),
                  sg.Button('Próximo', key='-NEW-ANALYSIS-NEXT3-'),
                  sg.Push()]],
            ])
        elif passo == 3:
            self.__create_window([
                [[sg.Checkbox('Relato no AIIM:            ', key='-NEW-ANALYSIS-RELATO-CHECK-',
                              default=self.has_overriden_field('relato'), enable_events=True),
                  sg.Multiline(default_text=
                               self.analysis_dict['infracoes'][self.infracao.filename]['relato']
                               if self.has_overriden_field('relato')
                               else AnalysisWizardWindow.infracao.report or '',
                               size=(10, 10),
                               expand_x=True, expand_y=True,
                               key='-NEW-ANALYSIS-RELATO-', auto_size_text=True,
                               disabled=not self.has_overriden_field('relato'))],
                 [sg.Checkbox('Relatório\nCircunstanciado:\n"No item <número>, "...',
                              key='-NEW-ANALYSIS-RELATORIO-CHECK-',
                              default=self.has_overriden_field('relatorio_circunstanciado'),
                              enable_events=True),
                  sg.Multiline(
                      default_text=
                      self.analysis_dict['infracoes'][self.infracao.filename]['relatorio_circunstanciado']
                      if self.has_overriden_field('relatorio_circunstanciado')
                      else AnalysisWizardWindow.infracao.relatorio_circunstanciado or '',
                      size=(10, 10),
                      expand_x=True, expand_y=True,
                      key='-NEW-ANALYSIS-RELATORIO-', auto_size_text=True,
                      disabled=not self.has_overriden_field('relatorio_circunstanciado'))],
                 [sg.Push(),
                  sg.Button('Anterior', key='-NEW-ANALYSIS-BACK2-'),
                  sg.Button('Próximo', key='-NEW-ANALYSIS-NEXT4-'),
                  sg.Push()]],
            ])
        elif passo == 4:
            proof_column = [[sg.Checkbox('Provas: ', key='-NEW-ANALYSIS-PROVA-CHECK-',
                                         default=self.has_overriden_field('provas'), enable_events=True)]]
            proof_column.extend(
                [[sg.Checkbox(AiimProof.proof_types[pt]['nome'],
                              key=f'-NEW-ANALYSIS-PROOF-CHECK-{pt}',
                              default=self.has_overriden_proof(pt) or self.has_default_proof(pt),
                              disabled=not self.has_overriden_field('provas'),
                              enable_events=True),
                  sg.InputText(key=f'-NEW-ANALYSIS-PROOF-TEXT-{pt}',
                               default_text=self.proof_description(pt),
                               disabled=not self.has_overriden_proof(pt),
                               expand_x=True)]
                 for pt in sorted(AiimProof.proof_types.keys())])
            self.__create_window([
                [
                    sg.Column(proof_column, expand_y=True, expand_x=True, justification='left'),
                    sg.Column([
                        [sg.Text('Ordem no Relatório Circunstanciado')],
                        [
                            sg.Column([[
                                sg.Listbox(values=
                                           [AiimProof.proof_types[p['tipo']]['nome']
                                            for p in
                                            self.analysis_dict['infracoes'][self.infracao.filename]['provas']]
                                           if self.has_overriden_field('provas')
                                           else [p.proof_type_name() for p in self.infracao.provas],
                                           key='-NEW-ANALYSIS-PROOF-LIST-',
                                           enable_events=True, size=(25, 4),
                                           disabled=not self.has_overriden_field(
                                               'provas') and not self.infracao.provas,
                                           expand_y=True),
                            ]], expand_y=True),
                            sg.Column([
                                [sg.Button('Antes', key='-NEW-ANALYSIS-PROOF-UP-',
                                           disabled=True, size=(7, None))],
                                [sg.Button('Depois', key='-NEW-ANALYSIS-PROOF-DOWN-',
                                           disabled=True, size=(7, None))]
                            ], expand_x=False, expand_y=False)
                        ],
                    ])
                ],
                [
                    sg.Push(),
                    sg.Button('Anterior', key='-NEW-ANALYSIS-BACK3-'),
                    sg.Input(key='-NEW-ANALYSIS-SAVE-', visible=False, enable_events=True),
                    sg.FileSaveAs('Salvar', enable_events=True,
                                  initial_folder=str(GeneralFunctions.get_user_path().absolute()),
                                  file_types=(('Arquivo de Análise', '.json'),)),
                    sg.Push()
                ]
            ])

    def __create_window(self, layout):
        if AnalysisWizardWindow.window:
            size = AnalysisWizardWindow.window.size
            AnalysisWizardWindow.window.close()
        else:
            size = AnalysisWizardWindow.default_size
        AnalysisWizardWindow.window = self
        super().__init__('Nova Análise', layout,
                         size=size,
                         auto_size_text=True, auto_size_buttons=True,
                         resizable=False, finalize=True,
                         default_element_size=(15, 1),
                         enable_close_attempted_event=True,
                         modal=True,
                         icon=GUIFunctions.app_icon)

    def handle_event(self, event, values):
        if event == sg.WIN_CLOSED:
            AnalysisWizardWindow.window = None
            AnalysisWizardWindow.analysis_dict = {}
            AnalysisWizardWindow.infracao = None
        elif event == '-NEW-ANALYSIS-NEXT2-':
            if not values['-NEW-ANALYSIS-INFRACTION-']:
                GUIFunctions.popup_erro('É necessário escolher uma infração para prosseguir!')
                return
            AnalysisWizardWindow.infracao = values['-NEW-ANALYSIS-INFRACTION-']
            self.analysis_dict['verificacao'] = values['-NEW-ANALYSIS-NAME-']
            self.analysis_dict['consulta'] = values['-NEW-ANALYSIS-SQL-']
            self.analysis_dict['infracoes'] = {AnalysisWizardWindow.infracao.filename: {}}
            self.analysis_dict['planilha_nome'] = values['-NEW-ANALYSIS-SHEET-']
            AnalysisWizardWindow(passo=2)
        elif event == '-NEW-ANALYSIS-NOTIFICATION-CHECK-':
            self['-NEW-ANALYSIS-NOTIFICATION-TITLE-'].update(disabled=not values['-NEW-ANALYSIS-NOTIFICATION-CHECK-'])
            self['-NEW-ANALYSIS-NOTIFICATION-BODY-'].update(disabled=not values['-NEW-ANALYSIS-NOTIFICATION-CHECK-'])
            self['-NEW-ANALYSIS-NOTIFICATION-ATTACHMENT-'].update(
                disabled=not values['-NEW-ANALYSIS-NOTIFICATION-CHECK-'])
        elif event in ('-NEW-ANALYSIS-NEXT3-', '-NEW-ANALYSIS-BACK1-'):
            if values['-NEW-ANALYSIS-NOTIFICATION-CHECK-']:
                if not self.analysis_dict.get('notificacao'):
                    self.analysis_dict['notificacao'] = {}
                self.analysis_dict['notificacao']['titulo'] = values['-NEW-ANALYSIS-NOTIFICATION-TITLE-']
                self.analysis_dict['notificacao']['corpo'] = values['-NEW-ANALYSIS-NOTIFICATION-BODY-']
                self.analysis_dict['notificacao']['anexo'] = values['-NEW-ANALYSIS-NOTIFICATION-ATTACHMENT-']
            else:
                if self.analysis_dict.get('notificacao'):
                    self.analysis_dict.pop('notificacao')
            AnalysisWizardWindow(passo=int(event[-2:-1]))
        elif event == '-NEW-ANALYSIS-RELATO-CHECK-':
            self['-NEW-ANALYSIS-RELATO-'].update(disabled=not values['-NEW-ANALYSIS-RELATO-CHECK-'])
        elif event == '-NEW-ANALYSIS-RELATORIO-CHECK-':
            self['-NEW-ANALYSIS-RELATORIO-'].update(disabled=not values['-NEW-ANALYSIS-RELATORIO-CHECK-'])
        elif event in ('-NEW-ANALYSIS-NEXT4-', '-NEW-ANALYSIS-BACK2-'):
            if not values['-NEW-ANALYSIS-RELATO-CHECK-'] and not values['-NEW-ANALYSIS-RELATORIO-CHECK-']:
                if isinstance(self.analysis_dict['infracoes'], dict) and self.has_infraction():
                    for k in ['relato', 'relatorio_circunstanciado']:
                        if k in self.analysis_dict['infracoes'][self.infracao.filename].keys():
                            self.analysis_dict['infracoes'][self.infracao.filename].pop(k)
            else:
                if isinstance(self.analysis_dict['infracoes'], list):
                    if self.infracao.filename not in self.analysis_dict['infracoes']:
                        self.analysis_dict['infracoes'].append(self.infracao.filename)
                    self.analysis_dict['infracoes'] = {i: {} for i in self.analysis_dict['infracoes']}
                if values['-NEW-ANALYSIS-RELATO-CHECK-']:
                    self.analysis_dict['infracoes'][self.infracao.filename]['relato'] = values['-NEW-ANALYSIS-RELATO-']
                elif self.analysis_dict['infracoes'][self.infracao.filename].get('relato'):
                    self.analysis_dict['infracoes'][self.infracao.filename].pop('relato')

                if values['-NEW-ANALYSIS-RELATORIO-CHECK-']:
                    self.analysis_dict['infracoes'][self.infracao.filename]['relatorio_circunstanciado'] = values[
                        '-NEW-ANALYSIS-RELATORIO-']
                elif self.analysis_dict['infracoes'][self.infracao.filename].get('relatorio_circunstanciado'):
                    self.analysis_dict['infracoes'][self.infracao.filename].pop('relatorio_circunstanciado')

            AnalysisWizardWindow(passo=int(event[-2:-1]))
        elif event == '-NEW-ANALYSIS-PROVA-CHECK-':
            lista = [AiimProof.proof_type_name(p['tipo'])
                     for p in self.analysis_dict['infracoes'][self.infracao.filename].get('provas', {})]\
                if values[event] else [p.proof_type_name() for p in self.infracao.provas]
            self['-NEW-ANALYSIS-PROOF-LIST-'].update(values=lista)
            self['-NEW-ANALYSIS-PROOF-UP-'].update(disabled=True)
            self['-NEW-ANALYSIS-PROOF-DOWN-'].update(disabled=True)
            for k in [k for k, v in values.items() if k.startswith('-NEW-ANALYSIS-PROOF-CHECK')]:
                self[k].update(disabled=not values['-NEW-ANALYSIS-PROVA-CHECK-'])
                proof_type = k[26:]
                if values[event]:
                    self[k].update(False)
                    self[f'-NEW-ANALYSIS-PROOF-TEXT-{proof_type}'].update('')
                else:
                    proofs = [p for p in self.infracao.provas if p.tipo == proof_type]
                    has_proof = len(proofs) > 0
                    proof = proofs[0] if has_proof else None
                    self[k].update(has_proof)
                    self[f'-NEW-ANALYSIS-PROOF-TEXT-{proof_type}'].update(proof.descricao if has_proof else '',
                                                                          disabled=True)
        elif event == '-NEW-ANALYSIS-PROOF-LIST-':
            if self[event].get() and self['-NEW-ANALYSIS-PROVA-CHECK-'].get():
                self['-NEW-ANALYSIS-PROOF-UP-'].update(disabled=
                                                       self[event].get_list_values()[0] == self[event].get()[0])
                self['-NEW-ANALYSIS-PROOF-DOWN-'].update(disabled=
                                                         self[event].get_list_values()[-1] == self[event].get()[0])
            else:
                self['-NEW-ANALYSIS-PROOF-UP-'].update(disabled=True)
                self['-NEW-ANALYSIS-PROOF-DOWN-'].update(disabled=True)
        elif event == '-NEW-ANALYSIS-PROOF-UP-':
            lista = self['-NEW-ANALYSIS-PROOF-LIST-'].get_list_values()
            item = self['-NEW-ANALYSIS-PROOF-LIST-'].get()[0]
            lista = lista[:lista.index(item) - 1] + [item, lista[lista.index(item) - 1]] + lista[lista.index(item) + 1:]
            self._change_proof_list(item, lista)
        elif event == '-NEW-ANALYSIS-PROOF-DOWN-':
            lista = self['-NEW-ANALYSIS-PROOF-LIST-'].get_list_values()
            item = self['-NEW-ANALYSIS-PROOF-LIST-'].get()[0]
            lista = lista[:lista.index(item)] + [lista[lista.index(item) + 1], item] + lista[lista.index(item) + 2:]
            self._change_proof_list(item, lista)
        elif event and event.startswith('-NEW-ANALYSIS-PROOF-CHECK-'):
            self[f'-NEW-ANALYSIS-PROOF-TEXT-{event[26:]}'].update('', disabled=not values[event])
            if values[event]:
                new_list = self['-NEW-ANALYSIS-PROOF-LIST-'].get_list_values()
                new_list.append(AiimProof.proof_types[event[26:]]['nome'])
                self._change_proof_list(None, new_list)
            else:
                new_list = self['-NEW-ANALYSIS-PROOF-LIST-'].get_list_values()
                new_list.remove(AiimProof.proof_types[event[26:]]['nome'])
                self._change_proof_list(None, new_list)
        elif event in ('-NEW-ANALYSIS-BACK3-', '-NEW-ANALYSIS-SAVE-'):
            if not values['-NEW-ANALYSIS-PROVA-CHECK-']:
                if self.has_infraction():
                    if 'provas' in self.analysis_dict['infracoes'][self.infracao.filename].keys():
                        self.analysis_dict['infracoes'][self.infracao.filename].pop('provas')
                if self['-NEW-ANALYSIS-PROOF-LIST-'].get_list_values() \
                        and self['-NEW-ANALYSIS-PROOF-LIST-'].get_list_values() != \
                        [p.proof_type_name() for p in self.infracao.provas]:
                    self.analysis_dict['infracoes'][self.infracao.filename]['provas'] = \
                        [{'tipo': AiimProof.get_proof_type_by_name(t),
                          'descricao': values[f'-NEW-ANALYSIS-PROOF-TEXT-{AiimProof.get_proof_type_by_name(t)}']}
                         for t in self['-NEW-ANALYSIS-PROOF-LIST-'].get_list_values()]
            else:
                if values['-NEW-ANALYSIS-PROVA-CHECK-']:
                    self.analysis_dict['infracoes'][self.infracao.filename]['provas'] = \
                        [{"tipo": AiimProof.get_proof_type_by_name(k),
                          "descricao": values[f'-NEW-ANALYSIS-PROOF-TEXT-{AiimProof.get_proof_type_by_name(k)}']}
                         for k in self['-NEW-ANALYSIS-PROOF-LIST-'].get_list_values()]
                else:
                    if self.analysis_dict['infracoes'][self.infracao.filename].get('provas'):
                        self.analysis_dict['infracoes'][self.infracao.filename].pop('provas')
            if event == '-NEW-ANALYSIS-BACK3-':
                AnalysisWizardWindow(passo=3)
            if event == '-NEW-ANALYSIS-SAVE-' and values['-NEW-ANALYSIS-SAVE-']:
                if all([not v for k, v in self.analysis_dict['infracoes'].items()]):
                    self.analysis_dict['infracoes'] = [k for k in self.analysis_dict['infracoes'].keys()]
                with open(values['-NEW-ANALYSIS-SAVE-'], mode='w') as outfile:
                    json.dump(self.analysis_dict, outfile, ensure_ascii=False, sort_keys=True, indent=2)
                Analysis.clear_user_analysis()
                Analysis.clear_audit_analysis()
                self.close()
