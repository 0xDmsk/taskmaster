# ---------------------------------
# Minimal, container-native zshrc
# ---------------------------------

export ZSH="/etc/zsh/oh-my-zsh"

# Containers are immutable: no auto-updates
zstyle ':omz:update' mode disabled

# Fast, predictable prompt
ZSH_THEME="robbyrussell"

# Minimal plugins only
plugins=(git aliases)

# Reduce surprises & latency
DISABLE_AUTO_TITLE="true"
DISABLE_MAGIC_FUNCTIONS="true"
DISABLE_UNTRACKED_FILES_DIRTY="true"

# History (ephemeral-friendly)
HISTSIZE=10000
SAVEHIST=10000
setopt hist_ignore_dups
setopt hist_ignore_space
setopt share_history

# Completion (cached in /tmp, safe for containers)
autoload -Uz compinit
compinit -d /tmp/zcompdump-$HOST

# Load Oh My Zsh
source $ZSH/oh-my-zsh.sh

# ------------------------------
# Keybindings (Mac muscle memory)
# ------------------------------

bindkey -e                                  # emacs key bindings
bindkey ' ' magic-space                     # history expansion on space
bindkey '^U' backward-kill-line             # ctrl + U
bindkey '^[[3;5~' kill-word                 # ctrl + delete
bindkey '^[[3~' delete-char                 # delete
bindkey '^[[1;5C' forward-word              # ctrl + →
bindkey '^[[1;5D' backward-word             # ctrl + ←
bindkey '^[[5~' beginning-of-buffer-or-history  # page up
bindkey '^[[6~' end-of-buffer-or-history        # page down
bindkey '^[[H' beginning-of-line            # home
bindkey '^[[F' end-of-line                  # end
bindkey '^[[Z' undo                         # shift + tab

# ------------------------------
# Completion system (Mac-like)
# ------------------------------

# Ensure completion system is initialized only once
autoload -Uz compinit
compinit -d /tmp/zcompdump-$HOST

# Completion UX tuning
zstyle ':completion:*' menu select
zstyle ':completion:*' auto-description 'specify: %d'
zstyle ':completion:*' completer _expand _complete
zstyle ':completion:*' format 'Completing %d'
zstyle ':completion:*' group-name ''
zstyle ':completion:*' list-colors ''
zstyle ':completion:*' list-prompt '%SAt %p: Hit TAB for more, or type to insert%s'
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}'
zstyle ':completion:*' rehash true
zstyle ':completion:*' select-prompt '%SScrolling active: selection at %p%s'
zstyle ':completion:*' use-compctl false
zstyle ':completion:*' verbose true

# Process completion (kill / fg / bg)
zstyle ':completion:*:kill:*' command \
  'ps -u $USER -o pid,%cpu,tty,cputime,cmd'


# ------------------------------
# Environment
# ------------------------------
export LANG=C.UTF-8
export EDITOR=vim
export PAGER=less

# ------------------------------
# tmux compatibility
# ------------------------------
# https://github.com/tmux/tmux/issues/223
if [[ -n "$TMUX" ]]; then
  unset zle_bracketed_paste
fi

# ------------------------------
# Micro-upgrades
# ------------------------------

# 1) Root prompt indicator (OPSEC hint)
# Red prompt when root, normal otherwise
if [[ $EUID -eq 0 ]]; then
  PROMPT='%F{red}%n@%m%f %F{yellow}%~%f %# '
fi

# 2) AWS profile awareness (quiet if unset)
aws_prompt() {
  [[ -n "$AWS_PROFILE" ]] && echo "%F{cyan}[aws:$AWS_PROFILE]%f "
}

# 3) Kubernetes context awareness (fast + safe)
kube_prompt() {
  command -v kubectl >/dev/null 2>&1 || return
  [[ -f "$HOME/.kube/config" ]] || return

  local ctx
  ctx=$(kubectl config current-context 2>/dev/null) || return
  echo "%F{blue}[k8s:$ctx]%f "
}

# Inject cloud context into right prompt (non-intrusive)
RPROMPT='$(aws_prompt)$(kube_prompt)'

# 4) SecLists mount detection (warn once)
if [[ ! -d "/usr/share/seclists" ]]; then
  print -P "%F{yellow}[!] SecLists not mounted at /usr/share/seclists%f"
fi

# 5) Per-project local overrides (optional)
# Allows .zshrc.local per working directory
autoload -U add-zsh-hook
load-local-zshrc() {
  [[ -f ./.zshrc.local ]] && source ./.zshrc.local
}
add-zsh-hook chpwd load-local-zshrc
load-local-zshrc

# ------------------------------
# Aliases
# ------------------------------
# System-wide aliases (container baseline)
source /etc/zsh/aliases
