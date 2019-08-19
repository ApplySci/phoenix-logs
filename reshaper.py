# -*- coding: utf-8 -*-
'''
Given a game as XML, completely reshape it, and return the new XML
'''

from sys import stderr
from constants import OUTCOMES, DRAWS
from lxml import etree

class Reshaper:
    '''
    Given a game as XML, completely reshape it, and return the new XML
    '''

    def __init__(self, game, log_id):
        self.sep = ['', '', '', '']
        self.discards = ['', '', '', '']
        self.cursor = None
        self.last_drawn = ['', '', '', '']
        self.log_id = log_id
        self.game = game
        self.current_hand = None

    def process(self):
        '''
        This is the heart of the class
        cycle over all events in this game, and build a new XML structure for it
        '''
        children = self.game.getchildren()
        child_count = len(children)
        ptr = 0
        game_out = etree.XML('<GAME id="%s"/>' % self.log_id)

        while ptr < child_count:
            # iterate over every event in game
            child = children[ptr]
            ptr += 1
            if child.tag == 'INIT':
                self.init_hand_vars(child)
            elif child.tag in ['SHUFFLE', 'GO', 'TAIKYOKU',]:
                pass
            elif child.tag == 'BYE':
                # TODO
                game_out.append(child)
            elif child.tag == 'UN' and self.current_hand is None:
                for key in child.attrib:
                    game_out.attrib[key] = child.attrib[key]
            elif child.tag == 'DORA':
                game_out.append(child)
            elif child.tag == 'AGARI':
                self.handle_win(child)
                game_out.append(self.current_hand)
                # TODO maybe check for double ron
            elif child.tag == 'RYUUKYOKU':
                self.handle_draw(child)
                game_out.append(self.current_hand)
            elif child.tag[0] in ('D', 'E', 'F', 'G'):
                self.current_hand.append(self.discard_to_xml(child))
            elif child.tag[0] in ('T', 'U', 'V', 'W'):
                self.current_hand.append(self.draw_to_xml(child))
            elif child.tag == 'N':
                self.process_call(child)
            elif child.tag == 'REACH':
                ptr = self.handle_riichi(ptr, child)
            else:
                # unknown tag
                self.log_error('ERROR unknown tag: %s in %s' % (child.tag, self.log_id))

        return game_out

    def init_hand_vars(self, child):
        ''' initialise instance variables that describe this hand '''
        for i in range(0, 4):
            self.sep[i] = ''
            self.discards[i] = ''
            self.last_drawn[i] = ''
        self.current_hand = etree.XML('<HAND />')
        for key in ['oya', 'hai0', 'hai1', 'hai2', 'hai3', 'ten',]:
            self.current_hand.attrib[key] = child.attrib[key]

    def handle_draw(self, child):
        self.current_hand.attrib['result'] = str(DRAWS[child.get('type') or 'exhaustive'])
        self.current_hand.attrib['scores'] = self.get_deltas(child)
        # TODO horrifically, it seems that the only way to find out what the
        #      dora was, when it was a draw, is to recreate the wall from
        #      the seed

    def handle_win(self, child):
        self.current_hand.attrib['result'] = str(OUTCOMES['Tsumo']
            if child.get('who') == child.get('fromWho') else
            OUTCOMES['Ron'])
        # TODO

    def process_call(self, child):
        ''' handle one called tile '''
        who = int(child.get('who'))
        meld = int(child.get('m'))
        meld_type = None
        #['chi', 'pon', 'kan', 'added kan', 'ron']
        if meld & 4 == 4: # bit 3 is 1
            # chi
            meld_type = 0
        elif meld & 12 == 8: # bit 4 is 1, bit 3 is 0
            # pon
            meld_type = 1
        elif meld & 28 == 16: # bit 5 is 1, bit 4 is 0
            # pon upgraded to kan
            meld_type = 3
        elif meld & 252 == 0: # bits 3-8 are zero
            # kan
            meld_type = 2
        else:
            self.log_error('unknown meld type %d in %s' %
                           (meld, self.log_id,))
            return
        # TODO

    def draw_to_xml(self, child):
        player = ('T', 'U', 'V', 'W').index(child.tag[0])
        tile_str = child.tag[1:4]
        self.last_drawn[player] = tile_str
        tile = self.convert_index_to_tile(int(tile_str))
        return etree.XML("<I who='%d' tile='%d'/>" % (player, tile,))

    def discard_to_xml(self, child):
        ''' return xml representing this discard '''
        player = ('D', 'E', 'F', 'G').index(child.tag[0])
        tile_str = child.tag[1:4]
        tile = self.convert_index_to_tile(int(tile_str))
        tsumogiri = 1 if self.last_drawn[player] == tile_str else 0
        xml = etree.XML("<O who='%d' tile='%d' tg='%d' />" % (player, tile, tsumogiri))
        return xml

    def handle_riichi(self, ptr, child):
        ''' riichi
        sequence is REACH (step=1)- DISCARD - REACH (step=2)
        '''
        if child.get('step') != '1':
            self.log_error('Error, first riichi step was not step one, %s' % self.log_id)
            return ptr
        player = int(child.get('who'))

        ptr += 1
        next_child = child.getnext()
        self.current_hand.append(etree.XML("<RIICHI who='%d'/>" % player))

        self.current_hand.append(self.discard_to_xml(next_child))

        second_next_child = next_child.getnext()
        if second_next_child.tag == 'REACH':
            return ptr + 1
        if second_next_child.tag == 'N':
            self.process_call(second_next_child, player)
            return ptr + 1

        return ptr

    @staticmethod
    def convert_index_to_tile(idx):
        ''' takes the tenhou tile index (1-136) and returns the id of this
        tile in the tiles table of this database
        '''
        #  order: man, pin, sou, winds, dragons
        # 1234 = 1 man; 5678=2 man; 17=red 5 main; 37=1 pin; 109=East
        out = 1 + (idx - 1) // 4
        if idx < 109 and idx % 4 == 1 and out % 9 == 5:
            # red 5s
            out = idx // 36 * 9
        else:
            out = out + (idx - 1) // 36
            if out > 30:
                # honours tile
                out -= 1

        return out

    @staticmethod
    def get_deltas(elem):
        ''' extract the score deltas for this hand
        NB sc element does not contain honba or lost/won riichi sticks.
        Won honba and riichi sticks are contained in 'ba': [honba count, riichi count]
        '''
        delta_list = elem.get('sc').split(',')
        return ','.join([delta_list[x] for x in (1, 3, 5, 7)])

    @staticmethod
    def log_error(txt):
        ''' log any error to stderr '''
        print(txt, file=stderr)
