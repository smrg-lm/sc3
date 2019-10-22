"""
Event another try.

A grandes rasgos, parent event define las llaves por defecto de los tipos de
eventos. El tipo de evento define lo que se ejecuta en la función play. Los
proto eventos también definen valores de llave por defecto pero de otra manera.

Las llaves parent compuestas de partials son globales, no se crea una por
instancia. La llave parent.partial.type es la que define el comportamiento de
play. Es como si estuviera invertida la jerarquía de tipos (o mal organizada).
El tipo del evento, que define el comportamiento particular, es una propiedad
de parent.partial.player.

Se podría definir todo como funciones a nivel de módulo, a cada función se
le pasa un dict (sería self) y se realizan las operaciones según estén o no
las llaves necesarias que cada función sabe.

*** También se podría usar eval/exec con locals y globals ***

Los eventos son un mini lenguaje declarativo, ver cómo se hacen los lenguajes
declarativos.

Se podrían definir las llaves por tipos de datos, Pitch: midinote, degree,
freq, gamut_t, chromatic_t, etc. Amplitude: amp, db, etc. Desde cada llave
se crea un objeto Pitch que es accesible desde otras llaves:

p = Pitch(freq=d['freq'])  # 'freq': 440
p.midinote  # 'midinote': 69
p.gamut_t = 0
p = Pitch(midinote=d['midinote'])  # o con otra sintaxis/interfaz.
p.freq

Sin embargo se estaría creando un objeto para cada llave, es algo a tener en
cuenta. Pero quedaría bien organizado. VER ABAJO, pero tener en cuenta qué
pasa si hay eventos parciales que comparten llaves, puede ser??

La opción de parent event es buena idea en sclang, pero a la manera de
agrupamiento jerárquico sería mejor... por ejemplo para la transposición,
se agrupa un conjunto de alturas, pero cómo sería? y cómo se llevaría con
los event patterns? (tal vez no bien en este último caso).

parent events son:
  default  (partials: pitch, amp, dur, buffer, server, player(types), midi)
  group  (partials: node) Es experimental para que el nodo quede como interfaz.
  synth  (partials: node) Ídem.

partial events son:
  pitch
  amp
  dur
  buffer
  server
  node
  player
  midi

event types son tipos de partial.player y son:
  note
  rest
  grain
  on
  set
  off
  kill
  group
  par_group
  bus
  fade_bus
  gen
  load
  read
  alloc
  free
  midi
  set_properties
  mono_off
  mono_set
  mono_note
  synth
  group
  tree
"""


# Si fuera necesario crear varias instancias se podría hacer que sea un objeto
# callable y reusable de igual manera que la metaclase. Incluso sin tanto
# glamur, con un método específico.
class Pitch():
    # la cadena de evaluación en sclang es: degree -> note -> midinote -> freq -> detuned_freq
    # si freq está dada no llama a midinote, y así siguiendo.
    # la otra posibilidad es que hayan distintas funciones para calcular detuned_freq
    # según la llave presente que defina pitch, pero el objeto pitch no sería general.
    _pitch_keys = ('freq', 'midinote', 'degree')

    def __init__(self, d):
        for key in self._pitch_keys:
            value = d.get(key)
            if value:
                break
        if not value:
            raise ValueError(f'no valid pitch key given')
        setattr(self, key, value)

        ...

    def __call__(self, d):
        self.__init__(d)
        # return None, usage is not intended to be assigned, may be weird.

    @property
    def freq(self):
        return self._freq or bi.midicps(self.midinote)

    @freq.setter
    def freq(self, value):
        self._freq = value

    @property
    def midinote(self):
        # pero las funciones fallan con None.
        return self._midinote or note_a_midi(self.note) or bi.cpsmidi(self._freq)  # está bien así? sigue por note, pero si no está vuevle a freq que es la anterior.

    @midinote.setter
    def midinote(self, value):
        self._midinote = value


p = Pitch(midinote=48)
p.freq
p(freq=330)
p.midinote
