package com.example.calculator

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.example.calculator.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    private var currentInput = StringBuilder()
    private var operator = ""
    private var firstOperand = 0.0
    private var justCalculated = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setupClickListeners()
    }

    private fun setupClickListeners() {
        with(binding) {
            btn0.setOnClickListener { appendDigit("0") }
            btn1.setOnClickListener { appendDigit("1") }
            btn2.setOnClickListener { appendDigit("2") }
            btn3.setOnClickListener { appendDigit("3") }
            btn4.setOnClickListener { appendDigit("4") }
            btn5.setOnClickListener { appendDigit("5") }
            btn6.setOnClickListener { appendDigit("6") }
            btn7.setOnClickListener { appendDigit("7") }
            btn8.setOnClickListener { appendDigit("8") }
            btn9.setOnClickListener { appendDigit("9") }
            btnDot.setOnClickListener { appendDot() }
            btnClear.setOnClickListener { clear() }
            btnPlusMinus.setOnClickListener { toggleSign() }
            btnPercent.setOnClickListener { applyPercent() }
            btnPlus.setOnClickListener { setOperator("+") }
            btnMinus.setOnClickListener { setOperator("-") }
            btnMultiply.setOnClickListener { setOperator("×") }
            btnDivide.setOnClickListener { setOperator("÷") }
            btnEquals.setOnClickListener { calculate() }
        }
    }

    private fun appendDigit(digit: String) {
        if (justCalculated) {
            currentInput.clear()
            justCalculated = false
        }
        if (currentInput.toString() == "0") currentInput.clear()
        currentInput.append(digit)
        binding.tvDisplay.text = currentInput.toString()
        binding.btnClear.text = "C"
    }

    private fun appendDot() {
        if (justCalculated) {
            currentInput.clear()
            currentInput.append("0")
            justCalculated = false
        }
        if (currentInput.isEmpty()) currentInput.append("0")
        if (!currentInput.contains(".")) {
            currentInput.append(".")
            binding.tvDisplay.text = currentInput.toString()
        }
    }

    private fun clear() {
        if (binding.btnClear.text == "C" && currentInput.isNotEmpty()) {
            currentInput.clear()
            binding.tvDisplay.text = "0"
            binding.btnClear.text = "AC"
        } else {
            currentInput.clear()
            operator = ""
            firstOperand = 0.0
            justCalculated = false
            binding.tvDisplay.text = "0"
            binding.tvExpression.text = ""
            binding.btnClear.text = "AC"
        }
    }

    private fun toggleSign() {
        val value = currentInput.toString().toDoubleOrNull() ?: return
        currentInput.clear()
        currentInput.append(formatNumber(-value))
        binding.tvDisplay.text = currentInput.toString()
    }

    private fun applyPercent() {
        val value = currentInput.toString().toDoubleOrNull() ?: return
        currentInput.clear()
        currentInput.append(formatNumber(value / 100.0))
        binding.tvDisplay.text = currentInput.toString()
    }

    private fun setOperator(op: String) {
        if (currentInput.isNotEmpty()) {
            firstOperand = currentInput.toString().toDoubleOrNull() ?: 0.0
        }
        binding.tvExpression.text = "${formatNumber(firstOperand)} $op"
        currentInput.clear()
        operator = op
        justCalculated = false
    }

    private fun calculate() {
        if (operator.isEmpty() || currentInput.isEmpty()) return
        val secondOperand = currentInput.toString().toDoubleOrNull() ?: return
        val result = when (operator) {
            "+" -> firstOperand + secondOperand
            "-" -> firstOperand - secondOperand
            "×" -> firstOperand * secondOperand
            "÷" -> if (secondOperand != 0.0) firstOperand / secondOperand else Double.NaN
            else -> secondOperand
        }
        binding.tvExpression.text = "${formatNumber(firstOperand)} $operator ${formatNumber(secondOperand)} ="
        val resultStr = if (result.isNaN()) "Error" else formatNumber(result)
        binding.tvDisplay.text = resultStr
        currentInput.clear()
        currentInput.append(resultStr)
        operator = ""
        justCalculated = true
        firstOperand = result
    }

    private fun formatNumber(value: Double): String {
        if (value.isNaN() || value.isInfinite()) return "Error"
        return if (value % 1.0 == 0.0) value.toLong().toString()
        else value.toBigDecimal().stripTrailingZeros().toPlainString()
    }
}
