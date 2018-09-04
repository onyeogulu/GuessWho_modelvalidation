
import numpy as np
import glob
import os
import json
import logging
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import flask

from game import *

logging.basicConfig(level=logging.INFO)

game = GuessWhoGame(data_file='./guesswho/data/test.json')

# characters = [
#     {'name': os.path.splitext(os.path.basename(filename))[0].split('-')[0],
#      'file': filename
#      } for filename in glob.glob('./images/*.jpg')
# ]
characters = game.get_characters()
questions = game.PROPERTIES
initial_hidden_state = json.dumps({c['id']: True for c in characters})
default_image = './images/unknown.jpg'


def create_test_data(out_file):
    idx = 0
    data = []
    for c in characters:
        idx += 1
        x = c
        x['id'] = idx
        x['properties'] = {}
        for k, v in questions.items():
            choice = np.random.randint(0, len(v))
            x['properties'][k] = v[choice]
        data.append(x)
    with open(out_file, 'w') as f:
        json.dump(data, f)


#create_test_data('./guesswho/data/test.json')

def reset_game():
    global game
    global characters
    global questions
    
    game = GuessWhoGame(data_file='./guesswho/data/test.json')
    characters = game.get_characters()
    questions = game.PROPERTIES


def get_character_options():
    return [{'label': c['name'], 'value': c['name']} for c in game.board.get_characters()]


def get_question_type_options():
    return [{'label': x, 'value': x} for x in questions.keys()]


def get_question_value_options(question_type):
    return [{'label': x, 'value': x} for x in questions[question_type]]


def get_answer(question_type, question_value):
    ok = question_type is not None and question_value is not None
    if not ok:
        return False, False

    ok, answer = game.human_player.ask_question((question_type, question_value))
    return ok, answer


def guess_character(name):
    character = game.board.get_character_by_name(name)
    ok, answer = game.human_player.guess_character(character)
    return ok, answer


def render_board_characters(player_id):
    elements = []
    for c in characters:
        elements.append(
            html.A(
                id='a-p{}-character-{}'.format(player_id, c['id']),
                href="javascript:clickCharacter({}, {})".format(player_id, c['id']),
                n_clicks=0,
                children=[
                    html.Figure(className='character-container has-text-centered', children=[
                        html.Img(id='img-p{}-character-{}'.format(player_id, c['id']), className='character-image', src=c['file']),
                        html.Figcaption(className='character-caption', children=c['name'])
                    ])
                ]
            )
        )
    return elements


def bulma_center(component):
    return html.Div(className='columns', children=[
        html.Div(className='column', children=[]),
        html.Div(className='column has-text-centered', children=[component]),
        html.Div(className='column', children=[])
    ])


def bulma_columns(components):
    return html.Div(className='columns has-text-centered', children=[
        html.Div(className='column', children=[c]) for c in components
    ])


def bulma_field(label, component):
    """
    Handle boiler plate stuff for putting a label on a dcc / input field
    """
    return html.Div(className='field', children=[
        html.Label(className='label', children=label),
        html.Div(className='control', children=[component])
    ])


def bulma_modal(id, content=None, btn_text='OK', btn_class='is-info', active=False):
    """
    Create a modal (overlay) in bulma format
    """
    return html.Div(className='modal {}'.format('is-active' if active else ''), id='{}-modal'.format(id), children=[
        html.Div(className='modal-background'),
        html.Div(className='modal-content', children=[
            html.Div(className='box', children=[
                html.Div(className='content', children=[
                    html.Div(id='{}-modal-content'.format(id), children=content),
                    html.Button(id='{}-modal-button'.format(id),
                                className='button is-medium {}'.format(btn_class),
                                n_clicks=0,
                                children=btn_text
                                )
                ])
            ])
        ])
    ])


app = dash.Dash()
#app.css.append_css({'external_url': 'https://cdnjs.cloudflare.com/ajax/libs/bulma/0.7.1/css/bulma.min.css'})

app.layout = html.Div(children=[
    bulma_columns([
        html.Img(className='header-logo', src='./images/guesswho_logo.png'),
        '',
        html.Img(className='header-logo', src='./images/Logo_datasciencelab.png')
    ]),

    # Computer player board
    html.Div(className='character-board panel', children=[
        html.P(className="panel-heading", children="Computer"),
        html.Div(className="panel-block is-block", children=[
            html.Div(id="computer-board", children=render_board_characters(player_id=1)),
            html.Progress(id='computer-progress', className="progress is-info", value="0", max="100"),
            html.Div(id='output-hidden-state', accessKey=initial_hidden_state)
        ])
    ]),

    # Select computer difficulty and character
    bulma_center(
        html.Div(id='computer-character', className='level', children=[
            html.Div(className='level-left', children=[
                html.Div(className='level-item', children=[
                    bulma_field(label="Select computer difficulty",
                                component=dcc.Dropdown(id='input-computer-mode',
                                                       options=[{'label': 'Hard', 'value': 'hard'},
                                                                {'label': 'Easy', 'value': 'easy'}],
                                                       value='hard'
                                                       )
                                )
                ]),
                html.Div(className='level-item', children=[
                    bulma_field(label='Select computer character',
                                component=dcc.Dropdown(id='input-character-select', options=get_character_options())
                                )
                ]),
                html.Div(className='level-item', children=[
                    html.Img(id='output-selected-character', src=default_image)
                ])
            ]),
            html.Div(className='level-right', children=[])
        ])
    ),
    dcc.Input(id='output-dummy-1', type='hidden', className='is-hidden', value=''),
    dcc.Input(id='output-dummy-2', type='hidden', className='is-hidden', value=''),

    # Human player board
    html.Div(className='character-board panel', children=[
        html.P(id="player-name", className="panel-heading", children="Player"),
        html.Div(className="panel-block is-block", children=[
            html.Div(id='player-board', children=render_board_characters(player_id=2)),
            html.Progress(id='player-progress', className="progress is-danger", value="0", max="100"),
            html.Div(className='columns', children=[
                html.Div(className='column', children=[
                    html.H4('Select your next question:')
                ]),
                html.Div(className='column', children=[
                    bulma_field(label='Category:',
                                component=dcc.Dropdown(id='input-question-type',
                                                       options=get_question_type_options())
                                )
                ]),
                html.Div(className='column', children=[
                    bulma_field('Options:', dcc.Dropdown(id='input-question-value', options=[], multi=False))
                ]),
                html.Div(className='column', children=[
                    bulma_field(label=[html.Span(className='is-invisible', children='.')],
                                component=html.Button(id='input-question-button',
                                                      className='button is-info is-inverted',
                                                      n_clicks=0,
                                                      children='Ask!'
                                                      )
                                )
                ])
            ]),
            html.Div(className='columns', children=[
                html.Div(className='column', children=[
                    html.H4('...or make a guess!')
                ]),
                html.Div(className='column is-half', children=[
                    bulma_field(label='Pick a character',
                                component=dcc.Dropdown(id='input-character-guess',
                                                       options=get_character_options(),
                                                       multi=False
                                                       )
                                )
                ]),
                html.Div(className='column', children=[
                    bulma_field(label=[html.Span(className='is-invisible', children='.')],
                                component=html.Button(id='input-guess-button',
                                                      className='button is-info is-inverted',
                                                      n_clicks=0,
                                                      children='Guess!'
                                                      )
                                )
                ])
            ]),
            html.Div([
                bulma_field(label='Answer', component=html.Div(id='output-question-answer', children=''))
            ]),
            html.Div(id='output-hidden-guess', accessKey="")
        ])
    ]),

    # Bottom part
    bulma_center(
        html.Button(id='input-endturn-button', className='button is-info is-large', n_clicks=0, children='End turn')
    ),

    html.Div(className='modal', id='end-modal', children=[
        html.Div(className='modal-background'),
        html.Div(className='modal-content', children=[
            html.Div(className='box', children=[
                html.Div(className='content', children=[
                    html.Div(id='end-modal-content', children=''),
                    html.Button(id='end-modal-button', className='button is-large', n_clicks=0, children='End game')
                ])
            ])
        ]),
        html.Button(className="modal-close is-large")
    ]),

    bulma_modal(id='waiting', content='Waiting for computer to move...'),

    bulma_modal(id='feedback'),

    bulma_modal(id='intro',
                content=[
                    html.Img(className='header-logo', src='./images/guesswho_logo.png'),
                    html.Br(), html.Br(),
                    html.Div("Welcome! To play a game:"),
                    html.Ul(children=[
                        html.Li("Start a new game"),
                        html.Li("Select a character for your opponent"),
                        html.Li("You're allowed to start, so go ahead and ask a question, or make a guess if you're feeling confident"),
                        html.Li("Click 'End turn' and wait for the computer to move")
                    ])
                ],
                btn_text='Start game!',
                btn_class='is-success',
                active=True
                ),

    html.Div(' ', id='spacer')
])


@app.server.route('/images/<path:path>')
def serve_images(path):
    """
    Pass local images to the web server
    """
    root_dir = os.getcwd()
    return flask.send_from_directory(os.path.join(root_dir, 'images'), path)


@app.callback(
    Output('intro-modal', 'className'),
    [Input('intro-modal-button', 'n_clicks')]
)
def start_game(_):
    """
    Start a new game with the modal button
    """
    if _ is None or _ == 0:
        return 'modal is-active'
    reset_game()
    return 'modal'


@app.callback(
    Output('output-dummy-2', 'value'),
    [Input(component_id='input-computer-mode', component_property='value')]
)
def set_difficulty(difficulty):
    """
    Set difficulty level with pulldown
    """
    if difficulty == 'hard':
        game.set_computer_mode('best')
    elif difficulty == 'easy':
        game.set_computer_mode('random')
    else:
        pass
    return ''


@app.callback(
    Output(component_id='output-selected-character', component_property='src'),
    [Input(component_id='input-character-select', component_property='value')]
)
def select_character(name):
    """
    Select computer character using pulldown
    """
    if name is None:
        return default_image

    logging.info("Setting computer character to {}".format(name))
    for c in characters:
        if c['name'] == name:
            game.set_computer_character(name)
            return c['file']
    raise ValueError("Character '{}' not found".format(name))


@app.callback(
    Output(component_id='input-question-value', component_property='options'),
    [Input(component_id='input-question-type', component_property='value')]
)
def set_question_options(question_type):
    """
    Fill pulldown options for questions
    """
    if question_type is None:
        return []
    return get_question_value_options(question_type)


@app.callback(
    Output('output-question-answer', 'children'),
    [Input('input-question-button', 'n_clicks')],
    [State('input-question-type', 'value'),
     State('input-question-value', 'value')],
)
def ask_question(_, question_type, question_value):
    """
    Ask a quesiton using the information in the pulldowns
    """
    if _ is None or _ == 0:
        return ''
    logging.info('{}: {}'.format(question_type, question_value))
    ok, answer = get_answer(question_type, question_value)
    if not ok:
        return 'You\'ve already made a move. Click "End turn".'
    else:
        return '{}, {} {} {}'.format(
            'Yes' if answer else 'No',
            question_type,
            'is' if answer else 'is not',
            question_value
        )


@app.callback(
    Output('output-hidden-guess', 'accessKey'),
    [Input('input-guess-button', 'n_clicks')],
    [State('input-character-guess', 'value')],
)
def make_guess(_, character_name):
    """
    Guess character selected in pulldown
    """
    if _ is None or _ == 0:
        return ''
    logging.info('Player is guessing for character {}'.format(character_name))
    ok, answer = guess_character(character_name)
    if not ok:
        logging.info("No answer received for guess")
        return '9'
    if answer:
        logging.info("Guess is correct! Player has won!")
        return '1'
    else:
        logging.info("Guess is incorrect")
        return '0'


@app.callback(
    Output('output-hidden-state', 'accessKey'),
    [Input('input-endturn-button', 'n_clicks')]
)
def end_human_turn(_):
    """
    Let computer player make a move and return updated game state to the front-end
    """
    if _ is None or _ == 0:
        return initial_hidden_state
    game.end_turn()
    game_finished, computer_move = game.do_computer_move()
    if game_finished:
        logging.info("Computer has won!")
        reset_game()
    logging.info(computer_move)
    return json.dumps(computer_move)


@app.callback(
    Output('waiting-modal', 'className'),
    [Input('output-hidden-state', 'accessKey')]
)
def close_waiting_modal(_):
    """
    Close the waiting modal once the game state has been updated (computer's turn is finished)
    """
    return 'modal'


@app.callback(
    Output('end-modal', 'className'),
    [Input('end-modal-button', 'n_clicks')]
)
def end_game(_):
    """
    Doesn't really do much since the front-end will reload and the game will be re-initialized
    """
    if _ > 0:
        game.end()

    return 'modal'


if __name__ == '__main__':
    app.run_server(debug=True, port=8123)
