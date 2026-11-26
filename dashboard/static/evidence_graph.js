/* Shared Cytoscape graph for the engagement evidence graph and the surface
   lineage graph. Graph payloads ({nodes, edges, stats}) are built server-side
   by dashboard/graph.py.

   EvidenceGraph.mount(root, {url}) wires a graph into `root`, finding its parts
   by data-graph attributes so several graphs can share a page:
     canvas, drawer, stats            required
     fit, expand, gaps, linked-only   optional controls
   Returns {cy, load(url)}; load() swaps in another payload (lineage per item).

   Node text comes from tool output and LLM-authored records, so the drawer only
   ever writes it through textContent. */
(function() {
    var STATUS = {COMPLETED: '#3fb950', FAILED: '#f85149', RUNNING: '#39d353',
                  QUEUED: '#388bfd', CLAIMED: '#d29922', CANCELLED: '#8b949e'};
    var SEVERITY = {Critical: '#f85149', High: '#ffa657', Medium: '#d29922',
                    Low: '#58a6ff', Info: '#8b949e'};
    var REL = {runs: '#484f58', depends_on: '#8b949e', evidences: '#3fb950',
               proves: '#f85149', impacts: '#d2a8ff', discovers: '#39c5cf',
               tested_by: '#a371f7', affects: '#f85149', contains: '#484f58',
               abused_in: '#d29922'};
    var FLAG_TEXT = {
        no_execution: 'No execution linked as evidence (source_execution_id / evidence).',
        unevidenced: 'High/Critical attack path with no linked execution or finding.',
        no_interpretation: 'Completed without an interpretation.',
        untagged: 'Linked from the report but not tagged to this engagement.',
        untested: 'Mapped but never tested.'
    };

    function nodeColor(n) {
        if (n.kind === 'execution') return STATUS[n.status] || '#8b949e';
        if (n.kind === 'finding') return SEVERITY[n.severity] || '#8b949e';
        if (n.kind === 'attack_path') return '#d29922';
        if (n.kind === 'asset') return '#39c5cf';
        if (n.kind === 'goal') return '#3fb950';
        if (n.kind === 'endpoint' || n.kind === 'functionality') return '#a371f7';
        return '#8b949e';
    }

    var STYLE = [
        {selector: 'node', style: {
            'shape': 'round-rectangle', 'width': 190, 'height': 44,
            'background-color': '#161b22', 'border-width': 3, 'border-color': 'data(color)',
            'label': 'data(label)', 'color': '#e6edf3', 'font-size': 10,
            'text-wrap': 'wrap', 'text-max-width': 170, 'text-valign': 'center',
            'text-halign': 'center'
        }},
        {selector: 'node[kind = "target"]', style: {'shape': 'rectangle', 'background-color': '#21262d', 'font-weight': 600}},
        {selector: 'node[kind = "asset"], node[kind = "goal"]', style: {'shape': 'ellipse', 'width': 160}},
        {selector: 'node[kind = "attack_path"]', style: {'shape': 'cut-rectangle'}},
        {selector: 'node[kind = "endpoint"]', style: {'shape': 'tag', 'font-family': 'monospace'}},
        {selector: 'node[kind = "functionality"]', style: {'shape': 'barrel', 'font-weight': 600}},
        {selector: 'node[?focus]', style: {'border-width': 5, 'background-color': '#2a1f3d'}},
        {selector: '.gap', style: {
            'background-color': '#3d1d1f', 'border-style': 'dashed',
            'underlay-color': '#f85149', 'underlay-opacity': 0.5, 'underlay-padding': 8
        }},
        {selector: 'node:selected', style: {'background-color': '#1f3a5f'}},
        {selector: 'edge', style: {
            'width': 1.5, 'curve-style': 'bezier', 'target-arrow-shape': 'triangle',
            'line-color': 'data(color)', 'target-arrow-color': 'data(color)', 'arrow-scale': 0.8
        }},
        {selector: 'edge[rel = "runs"], edge[rel = "contains"]', style: {'line-style': 'dotted'}},
        {selector: '.faded', style: {'opacity': 0.15}}
    ];

    function row(dl, label, value) {
        if (value === undefined || value === null || value === '') return;
        var dt = document.createElement('dt'); dt.textContent = label;
        var dd = document.createElement('dd'); dd.textContent = value;
        dl.appendChild(dt); dl.appendChild(dd);
    }

    function link(parent, href, text) {
        var a = document.createElement('a');
        a.className = 'action-btn'; a.href = href; a.textContent = text;
        parent.appendChild(a);
    }

    function mount(root, opts) {
        function part(name) { return root.querySelector('[data-graph="' + name + '"]'); }
        var container = part('canvas'), drawer = part('drawer'), statsEl = part('stats');
        if (!container || typeof cytoscape === 'undefined') {
            if (statsEl) statsEl.textContent = 'Graph library failed to load.';
            return null;
        }
        var engagementId = opts.engagementId;
        var cy = cytoscape({container: container, wheelSensitivity: 0.2, minZoom: 0.1,
                            maxZoom: 2.5, style: STYLE});

        /* Dagre for everything with an edge; isolated nodes (typically unbacked
           findings) go in a grid underneath, so a long tail of loose nodes doesn't
           stretch rank 0 and shrink the real chains to nothing. */
        function layout() {
            var visible = cy.elements().filter(function(el) { return el.style('display') !== 'none'; });
            var isolated = visible.nodes().filter(function(n) {
                return n.connectedEdges().filter(function(e) { return e.style('display') !== 'none'; }).empty();
            });
            var linked = visible.not(isolated);
            var y = 0, x = 0, width = 1200;
            if (linked.nonempty()) {
                linked.layout({name: 'dagre', rankDir: 'LR', nodeSep: 14, rankSep: 70, animate: false}).run();
                var bb = linked.boundingBox();
                x = bb.x1; y = bb.y2 + 90; width = Math.max(bb.w, 1200);
            }
            if (isolated.nonempty()) {
                var cols = Math.max(1, Math.floor(width / 210));
                isolated.layout({name: 'grid', cols: cols, avoidOverlap: true, condense: true, animate: false,
                                 boundingBox: {x1: x, y1: y, w: cols * 210,
                                               h: Math.ceil(isolated.length / cols) * 60}}).run();
            }
            cy.fit(visible, 30);
        }

        function showDrawer(d) {
            drawer.replaceChildren();
            var h = document.createElement('h4'); h.textContent = d.label;
            drawer.appendChild(h);
            var dl = document.createElement('dl'); dl.className = 'detail-list';
            row(dl, 'Kind', d.kind.replace('_', ' '));
            if (d.kind === 'execution') {
                row(dl, 'Status', d.status); row(dl, 'Phase', d.phase);
                row(dl, 'Target', d.target); row(dl, 'Created', d.created_at);
                row(dl, 'Execution ID', d.execution_id);
            } else if (d.kind === 'finding') {
                row(dl, 'Severity', d.severity); row(dl, 'Status', d.status); row(dl, 'Affected', d.affected);
            } else if (d.kind === 'attack_path') {
                row(dl, 'Priority', d.priority); row(dl, 'Likelihood', d.likelihood);
                row(dl, 'Impact', d.impact); row(dl, 'Threat model', d.threat_model);
                row(dl, 'Description', d.description);
            } else if (d.kind === 'asset' || d.kind === 'goal') {
                row(dl, 'Threat model', d.threat_model); row(dl, 'Description', d.description);
            } else if (d.kind === 'endpoint' || d.kind === 'functionality') {
                row(dl, 'Ref', d.ref); row(dl, 'Coverage', d.status);
                row(dl, 'Identity', d.key); row(dl, 'Attack surface', d.attack_surface_ref);
                row(dl, 'Description', d.description);
            }
            drawer.appendChild(dl);
            (d.flags || []).forEach(function(f) {
                var p = document.createElement('p'); p.className = 'graph-flag';
                p.textContent = FLAG_TEXT[f] || f;
                drawer.appendChild(p);
            });
            var actions = document.createElement('div'); actions.className = 'graph-actions';
            if (d.kind === 'execution') link(actions, '/executions#exec:' + d.execution_id, 'Open execution');
            if (d.kind === 'finding') {
                link(actions, '/reporting/engagements/' + engagementId + '#finding-' + d.finding_id, 'Show in list');
                link(actions, '/reporting/findings/' + d.finding_id + '/edit', 'Edit');
            }
            if (d.kind === 'target') link(actions, '/targets#target:' + d.label, 'Open target');
            if ((d.kind === 'endpoint' || d.kind === 'functionality') && d.item_id) {
                link(actions, '/reporting/engagements/' + engagementId + '/surface#surface:' + d.item_id, 'Show in matrix');
            }
            drawer.appendChild(actions);
        }

        function checked(name, fallback) {
            var el = part(name);
            return el ? el.checked : fallback;
        }

        function applyFilters() {
            var gaps = checked('gaps', true);
            cy.nodes().forEach(function(n) { n.toggleClass('gap', gaps && (n.data('flags') || []).length > 0); });
            var linkedOnly = checked('linked-only', false);
            cy.batch(function() {
                cy.elements().style('display', 'element');
                if (linkedOnly) {
                    var reportNodes = 'node[kind = "finding"], node[kind = "attack_path"]';
                    cy.nodes('[kind = "execution"]').forEach(function(n) {
                        if (n.successors(reportNodes).empty()) n.style('display', 'none');
                    });
                    cy.nodes('[kind = "target"]').forEach(function(n) {
                        if (n.outgoers('node').filter(function(c) { return c.style('display') !== 'none'; }).empty()) {
                            n.style('display', 'none');
                        }
                    });
                }
            });
            layout();
        }

        cy.on('tap', 'node', function(evt) {
            var node = evt.target;
            showDrawer(node.data());
            cy.elements().addClass('faded');
            node.closedNeighborhood().union(node.predecessors()).union(node.successors()).removeClass('faded');
        });
        cy.on('tap', function(evt) {
            if (evt.target === cy) cy.elements().removeClass('faded');
        });

        var fitBtn = part('fit');
        if (fitBtn) fitBtn.addEventListener('click', function() { cy.fit(undefined, 30); });

        /* Full-window overlay: the canvas changes size, so Cytoscape has to
           re-measure before re-fitting. */
        var expandBtn = part('expand');
        function setExpanded(on) {
            root.classList.toggle('graph-expanded', on);
            document.body.classList.toggle('graph-overlay-open', on);
            if (expandBtn) expandBtn.textContent = on ? 'Close' : 'Expand';
            cy.resize();
            cy.fit(undefined, 30);
        }
        if (expandBtn) {
            expandBtn.addEventListener('click', function() {
                setExpanded(!root.classList.contains('graph-expanded'));
            });
            document.addEventListener('keydown', function(evt) {
                if (evt.key === 'Escape' && root.classList.contains('graph-expanded')) setExpanded(false);
            });
        }
        ['gaps', 'linked-only'].forEach(function(name) {
            var el = part(name);
            if (el) el.addEventListener('change', applyFilters);
        });

        function load(url) {
            statsEl.textContent = 'Loading…';
            return fetch(url)
                .then(function(r) { if (!r.ok) throw new Error(r.status); return r.json(); })
                .then(function(g) {
                    cy.elements().remove();
                    drawer.replaceChildren();
                    var hint = document.createElement('p'); hint.className = 'graph-hint';
                    hint.textContent = 'Click a node for details.';
                    drawer.appendChild(hint);
                    cy.add(g.nodes.map(function(n) {
                        n.color = nodeColor(n);
                        return {group: 'nodes', data: n};
                    }).concat(g.edges.map(function(e) {
                        return {group: 'edges', data: {source: e.source, target: e.target, rel: e.rel,
                                                       color: REL[e.rel] || '#8b949e'}};
                    })));
                    statsEl.textContent = g.nodes.length
                        ? g.stats.nodes + ' nodes · ' + g.stats.edges + ' edges · ' + g.stats.flagged + ' gaps'
                        : 'Nothing linked yet.';
                    cy.resize();
                    applyFilters();
                    return g;
                })
                .catch(function() { statsEl.textContent = 'Failed to load graph.'; });
        }

        if (opts.url) load(opts.url);
        return {cy: cy, load: load};
    }

    window.EvidenceGraph = {mount: mount};
})();
