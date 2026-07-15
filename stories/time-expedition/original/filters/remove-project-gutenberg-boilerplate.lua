local terminal_headings = {
  ["TRANSCRIBER'S NOTES"] = true,
  ["BACK COVER"] = true,
  ["BACK COVER:"] = true,
}

local leading_note_markers = {
  ["TRANSCRIBER'S NOTE"] = true,
  ["TRANSCRIBER'S NOTE:"] = true,
}

local function normalized_text(block)
  local text = pandoc.utils.stringify(block):gsub("’", "'"):upper():gsub("%s+", " ")
  return text:match("^%s*(.-)%s*$")
end

local function has_class(div, wanted)
  for _, class in ipairs(div.classes) do
    if class == wanted then
      return true
    end
  end
  return false
end

function Div(div)
  if has_class(div, "pg-boilerplate") then
    return {}
  end
end

function Image()
  return {}
end

function Header(header)
  if normalized_text(header) == "FRONT COVER:" then
    return {}
  end
end

function Pandoc(doc)
  local kept = pandoc.List()
  local start_index = 1
  local leading_note_seen = false
  local dropping_terminal_notes = false

  for index, block in ipairs(doc.blocks) do
    if block.t == "HorizontalRule" then
      if leading_note_seen then
        start_index = index + 1
      end
      break
    elseif leading_note_markers[normalized_text(block)] then
      leading_note_seen = true
    end
  end

  for index, block in ipairs(doc.blocks) do
    if index >= start_index then
      if block.t == "Header" and terminal_headings[normalized_text(block)] then
        dropping_terminal_notes = true
      end
      if not dropping_terminal_notes then
        kept:insert(block)
      end
    end
  end

  while #kept > 0 and
      (kept[1].t == "HorizontalRule" or normalized_text(kept[1]) == "") do
    kept:remove(1)
  end
  while #kept > 0 and
      (kept[#kept].t == "HorizontalRule" or normalized_text(kept[#kept]) == "") do
    kept:remove(#kept)
  end

  return pandoc.Pandoc(kept, doc.meta)
end
