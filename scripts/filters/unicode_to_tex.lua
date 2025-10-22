-- Pandoc Lua filter (ASCII-safe): Unicode math symbols → LaTeX commands
-- Only modifies Math nodes; leaves plain text untouched to avoid ensuremath.

local utf8 = utf8

local function replace_codepoints(s, map)
  local out = {}
  for _, cp in utf8.codes(s) do
    local repl = map[cp]
    if repl then table.insert(out, repl) else table.insert(out, utf8.char(cp)) end
  end
  return table.concat(out)
end

-- Minimal, safe mapping (extend as needed)
local MAP_CP = {
  -- geometry / shapes
  [0x2220] = "\\angle ",      -- ∠
  [0x25B3] = "\\triangle ",   -- △
  [0x25BD] = "\\triangledown ",-- ▽
  [0x00B0] = "^{\\circ}",      -- °

  -- relations / operations
  [0x2264] = "\\leq ",  -- ≤
  [0x2265] = "\\geq ",  -- ≥
  [0x2260] = "\\ne ",   -- ≠
  [0x2248] = "\\approx ",-- ≈
  [0x2261] = "\\equiv ", -- ≡
  [0x00D7] = "\\times ", -- ×
  [0x00F7] = "\\div ",   -- ÷
  [0x00B1] = "\\pm ",    -- ±

  -- sets
  [0x221E] = "\\infty ", -- ∞
  [0x222A] = "\\cup ",   -- ∪
  [0x2229] = "\\cap ",   -- ∩
  [0x2205] = "\\varnothing ", -- ∅
  [0x2208] = "\\in ",    -- ∈
  [0x2209] = "\\notin ", -- ∉

  -- arrows
  [0x2192] = "\\to ",          -- →
  [0x2190] = "\\leftarrow ",    -- ←
  [0x2194] = "\\leftrightarrow ", -- ↔
  [0x21A6] = "\\mapsto ",      -- ↦

  -- calculus
  [0x2202] = "\\partial ", -- ∂
  [0x2207] = "\\nabla ",   -- ∇
  [0x222B] = "\\int ",     -- ∫
  [0x222E] = "\\oint ",    -- ∮
  [0x2211] = "\\sum ",     -- ∑
  [0x220F] = "\\prod ",    -- ∏
}

function Math(m)
  local t = replace_codepoints(m.text, MAP_CP)
  -- Angle/triangle followed by letters → add braces for grouping
  t = t:gsub("\\angle%s*([A-Za-z]+)", "\\angle {%1}")
  m.text = t
  return m
end

function Str(s)
  return nil -- no text-level changes
end

-- Flatten ordered lists to plain paragraphs: "n. text"
function OrderedList(el)
  local out = {}
  local start = el.start or 1
  for i, item in ipairs(el.content) do
    local n = start + i - 1
    local text = pandoc.utils.stringify(item)
    text = text:gsub('^%s+', ''):gsub('%s+$', '')
    if text ~= '' then
      table.insert(out, pandoc.Para({ pandoc.Str(tostring(n) .. '. ' .. text) }))
    end
  end
  return out
end


