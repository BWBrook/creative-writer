local excluded_packaging_files = {
  ["endnotes.xhtml"] = true,
  ["imprint.xhtml"] = true,
  ["colophon.xhtml"] = true,
  ["uncopyright.xhtml"] = true,
}

local function is_excluded_packaging_target(target)
  local path = target:gsub("[#?].*$", "")
  local filename = path:match("([^/]+)$")
  return filename ~= nil and excluded_packaging_files[filename] == true
end

function Link(element)
  if is_excluded_packaging_target(element.target) then
    return {}
  end
  return element
end
