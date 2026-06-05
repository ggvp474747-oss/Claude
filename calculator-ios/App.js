import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View, TouchableOpacity, Dimensions } from 'react-native';
import { useState, useCallback } from 'react';

const { width } = Dimensions.get('window');
const BTN = (width - 5 * 12) / 4;

const BUTTONS = [
  ['AC', '+/-', '%', '÷'],
  ['7', '8', '9', '×'],
  ['4', '5', '6', '−'],
  ['1', '2', '3', '+'],
  ['0', '.', '='],
];

const COLOR = {
  top: '#a5a5a5',
  op: '#ff9f0a',
  num: '#333333',
};

export default function App() {
  const [display, setDisplay] = useState('0');
  const [prev, setPrev] = useState(null);
  const [op, setOp] = useState(null);
  const [waitNext, setWaitNext] = useState(false);
  const [expression, setExpression] = useState('');

  const fmt = useCallback((n) => {
    if (n === null || n === undefined) return '0';
    const s = Number(n);
    if (!isFinite(s)) return 'Ошибка';
    const str = parseFloat(s.toPrecision(10)).toString();
    if (str.length > 9) return parseFloat(s.toExponential(4)).toString();
    return str;
  }, []);

  const pressNum = useCallback((num) => {
    if (waitNext) {
      setDisplay(num === '.' ? '0.' : num);
      setWaitNext(false);
    } else {
      if (num === '.' && display.includes('.')) return;
      if (display === '0' && num !== '.') {
        setDisplay(num);
      } else {
        if (display.length >= 9) return;
        setDisplay(display + num);
      }
    }
  }, [display, waitNext]);

  const calculate = (a, b, operation) => {
    switch (operation) {
      case '+': return a + b;
      case '−': return a - b;
      case '×': return a * b;
      case '÷': return b !== 0 ? a / b : Infinity;
      default: return b;
    }
  };

  const pressOp = useCallback((nextOp) => {
    const current = parseFloat(display);
    if (prev !== null && !waitNext) {
      const result = calculate(prev, current, op);
      setDisplay(fmt(result));
      setPrev(result);
      setExpression(`${fmt(result)} ${nextOp}`);
    } else {
      setPrev(current);
      setExpression(`${fmt(current)} ${nextOp}`);
    }
    setOp(nextOp);
    setWaitNext(true);
  }, [display, prev, op, waitNext, fmt]);

  const pressEquals = useCallback(() => {
    if (op === null || prev === null) return;
    const current = parseFloat(display);
    const result = calculate(prev, current, op);
    setDisplay(fmt(result));
    setPrev(null);
    setOp(null);
    setWaitNext(true);
    setExpression('');
  }, [display, prev, op, fmt]);

  const pressAC = useCallback(() => {
    setDisplay('0');
    setPrev(null);
    setOp(null);
    setWaitNext(false);
    setExpression('');
  }, []);

  const pressToggle = useCallback(() => {
    setDisplay(fmt(parseFloat(display) * -1));
  }, [display, fmt]);

  const pressPercent = useCallback(() => {
    setDisplay(fmt(parseFloat(display) / 100));
  }, [display, fmt]);

  const handlePress = useCallback((btn) => {
    if (btn === 'AC' || btn === 'C') pressAC();
    else if (btn === '+/-') pressToggle();
    else if (btn === '%') pressPercent();
    else if (['+', '−', '×', '÷'].includes(btn)) pressOp(btn);
    else if (btn === '=') pressEquals();
    else pressNum(btn);
  }, [pressAC, pressToggle, pressPercent, pressOp, pressEquals, pressNum]);

  const getLabel = (btn) => (btn === 'AC' && display !== '0' ? 'C' : btn);

  const isActiveOp = (btn) => op === btn && waitNext;

  const getBtnStyle = (btn) => {
    if (['+', '−', '×', '÷', '='].includes(btn)) {
      return [styles.btn, { backgroundColor: isActiveOp(btn) ? '#fff' : COLOR.op }];
    }
    if (['AC', 'C', '+/-', '%'].includes(btn)) return [styles.btn, { backgroundColor: COLOR.top }];
    if (btn === '0') return [styles.btn, styles.btnZero];
    return [styles.btn, { backgroundColor: COLOR.num }];
  };

  const getTextStyle = (btn) => {
    if (['+', '−', '×', '÷', '='].includes(btn)) {
      return [styles.btnText, { color: isActiveOp(btn) ? COLOR.op : '#fff' }];
    }
    if (['AC', 'C', '+/-', '%'].includes(btn)) return [styles.btnText, { color: '#000' }];
    return [styles.btnText];
  };

  const fontSize = display.length > 7 ? 48 : display.length > 5 ? 64 : 80;

  return (
    <View style={styles.container}>
      <StatusBar style="light" />

      <View style={styles.display}>
        {expression ? <Text style={styles.expression}>{expression}</Text> : null}
        <Text style={[styles.result, { fontSize }]} numberOfLines={1} adjustsFontSizeToFit>
          {display}
        </Text>
      </View>

      <View style={styles.buttons}>
        {BUTTONS.map((row, i) => (
          <View key={i} style={styles.row}>
            {row.map((btn) => (
              <TouchableOpacity
                key={btn}
                style={getBtnStyle(btn)}
                onPress={() => handlePress(btn)}
                activeOpacity={0.7}
              >
                <Text style={getTextStyle(btn)}>{getLabel(btn)}</Text>
              </TouchableOpacity>
            ))}
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
    justifyContent: 'flex-end',
    paddingBottom: 40,
  },
  display: {
    paddingHorizontal: 20,
    paddingBottom: 12,
    alignItems: 'flex-end',
  },
  expression: {
    color: '#888',
    fontSize: 24,
    marginBottom: 4,
  },
  result: {
    color: '#fff',
    fontWeight: '200',
    letterSpacing: -2,
  },
  buttons: {
    paddingHorizontal: 12,
    gap: 12,
  },
  row: {
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'center',
  },
  btn: {
    width: BTN,
    height: BTN,
    borderRadius: BTN / 2,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLOR.num,
  },
  btnZero: {
    width: BTN * 2 + 12,
    alignItems: 'flex-start',
    paddingLeft: BTN / 3,
    borderRadius: BTN / 2,
    backgroundColor: COLOR.num,
  },
  btnText: {
    color: '#fff',
    fontSize: 32,
    fontWeight: '400',
  },
});
