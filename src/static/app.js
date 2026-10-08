"use strict";
const $ = (selector) => document.querySelector(selector);
const app = $("#app");
const modal = $("#modal");
const names = {inicio:"Visão geral",produtos:"Produtos",clientes:"Clientes",orcamento:"Orçamento",venda:"Nova venda",relatorio:"Relatório de vendas",banco:"Banco de dados"};
const state = {
  page: "inicio", products: [], customers: [], report: {vendas:[],resumo:{}}, filteredReport: null,
  carts: {orcamento:[],venda:[]}, discounts: {orcamento:"10",venda:"0"}, totals: {orcamento:null,venda:null},
  customerId: "", selectedResource: "View", resources: null, pending: false, search: {produtos:"",clientes:""},
  filters: {inicio:"",fim:""}, lastSale: null,
};
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const icon = (name) => `<svg class="icon" aria-hidden="true"><use href="#i-${name}"/></svg>`;
const money = value => new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"}).format(Number(value || 0));
const day = value => new Intl.DateTimeFormat("pt-BR",{day:"2-digit",month:"2-digit",year:"numeric",timeZone:"America/Sao_Paulo"}).format(new Date(value));
const hour = value => new Intl.DateTimeFormat("pt-BR",{hour:"2-digit",minute:"2-digit",second:"2-digit",timeZone:"America/Sao_Paulo"}).format(new Date(value));
const activeProducts = () => state.products.filter(p=>p.ativo);
const activeCustomers = () => state.customers.filter(c=>c.ativo);
const product = id => state.products.find(p=>p.id === Number(id));
const badge = (label, type="") => `<span class="badge ${type}">${esc(label)}</span>`;
const empty = text => `<div class="empty">${esc(text)}</div>`;
let toastTimer;
function toast(message, error=false) {
  const box = $("#toast"); box.textContent=message; box.className=`toast${error?" error":""}`; box.hidden=false;
  clearTimeout(toastTimer); toastTimer=setTimeout(()=>{box.hidden=true;},6000);
}
async function api(path, method="GET", data) {
  const result = await fetch(path,{method, headers:data?{"Content-Type":"application/json"}:{},body:data?JSON.stringify(data):undefined});
  const json = await result.json(); if(!result.ok) throw new Error(json.erro || "Falha ao consultar o sistema."); return json;
}
async function refresh() {
  [state.products,state.customers,state.report] = await Promise.all([api("/api/produtos"),api("/api/clientes"),api("/api/relatorio")]);
  if (!activeCustomers().some(c=>String(c.id)===String(state.customerId))) state.customerId=String(activeCustomers()[0]?.id || "");
}
function heading(title,subtitle,action="") {
  return `<div class="page-heading"><div><h1>${title}</h1><p class="subtitle">${subtitle}</p></div>${action}</div>`;
}
function stat(label,value,caption) {
  return `<div class="stat"><div class="stat-head">${label}</div><div class="stat-value">${value}</div><div class="stat-caption">${caption}</div></div>`;
}
function salesTable(rows, compact=false) {
  if(!rows.length) return empty("Nenhuma venda encontrada.");
  return `<div class="table-wrap"><table><thead><tr><th>Venda</th><th>Cliente</th>${compact?"":"<th>Data</th><th class=\"amount\">Unidades</th><th class=\"amount\">Desconto</th>"}<th class="amount">Total</th><th class="amount">Consulta</th></tr></thead><tbody>${rows.map(v=>`<tr><td class="nowrap">#${String(v.venda_id).padStart(3,"0")}</td><td><div class="entity">${esc(v.cliente_nome)}${compact?`<small>${day(v.data_venda)}</small>`:""}</div></td>${compact?"":`<td class="muted nowrap">${day(v.data_venda)}<br><small>${hour(v.data_venda)}</small></td><td class="amount">${v.unidades}</td><td class="amount">${Number(v.desconto_percentual).toLocaleString("pt-BR")}%</td>`}<td class="amount strong">${money(v.valor_total)}</td><td class="amount"><button class="text-action" data-action="detail" data-id="${v.venda_id}" aria-label="Detalhes da venda ${v.venda_id}">Detalhes</button></td></tr>`).join("")}</tbody></table></div>`;
}
function renderHome() {
  const summary=state.report.resumo; const low=activeProducts().filter(p=>p.estoque <= p.estoque_minimo);
  const rankings=new Map(); state.report.vendas.forEach(v=>rankings.set(v.cliente_nome,(rankings.get(v.cliente_nome)||0)+Number(v.valor_total)));
  const ranked=[...rankings].sort((a,b)=>b[1]-a[1]).slice(0,4);
  app.innerHTML=heading("Visão geral","Resumo das vendas e do estoque.",`<div class="button-row"><a class="button" href="#orcamento">Orçamento</a><a class="button primary" href="#venda">Nova venda</a></div>`)+
  `<div class="stats">${stat("Valor das vendas",money(summary.faturamento),"Todas as vendas registradas")}${stat("Vendas realizadas",summary.vendas||0,`${summary.unidades||0} unidades vendidas`)}${stat("Produtos ativos",activeProducts().length,"Disponíveis para novas vendas")}${stat("Estoque baixo",low.length,"No mínimo ou abaixo dele")}</div>
  <div class="home-layout"><section class="panel"><div class="panel-heading"><h2>Últimas vendas</h2><a href="#relatorio">Ver todas</a></div>${salesTable(state.report.vendas.slice(0,4),true)}</section>
  <section class="panel stock-reminder"><div class="panel-heading"><h2>Produtos para repor</h2></div><div class="panel-body">${low.length?low.slice(0,5).map(p=>`<div class="low-item"><div><h3>${esc(p.nome)}</h3><small>Estoque mínimo: ${p.estoque_minimo} un.</small></div><div class="low-number">${p.estoque}<small>un. disponíveis</small></div></div>`).join(""):empty("Nenhum produto abaixo do estoque mínimo.")}<a class="stock-link" href="#produtos">Consultar estoque</a></div></section></div>
  <div class="home-bottom"><section class="plain-section"><h2>Compras por cliente</h2>${ranked.length?`<table><thead><tr><th>Cliente</th><th class="amount">Valor acumulado</th></tr></thead><tbody>${ranked.map(([name,value])=>`<tr><td>${esc(name)}</td><td class="amount">${money(value)}</td></tr>`).join("")}</tbody></table>`:empty("Nenhuma compra registrada.")}</section>
  <section class="plain-section"><h2>Dados gerais</h2><dl class="home-totals"><div><dt>Clientes ativos</dt><dd>${activeCustomers().length}</dd></div><div><dt>Unidades em estoque</dt><dd>${activeProducts().reduce((s,p)=>s+p.estoque,0)}</dd></div><div><dt>Descontos concedidos</dt><dd>${money(summary.descontos)}</dd></div></dl></section></div>`;
}
function renderProducts() {
  app.innerHTML=heading("Produtos","Cadastro de produtos, preços e quantidades em estoque.",`<button class="button primary" data-action="edit-product">Novo produto</button>`)+
  `<section class="panel"><div class="toolbar"><label class="search-box">${icon("search")}<input id="search" data-search-type="produtos" aria-label="Buscar produto" placeholder="Buscar por produto ou categoria" value="${esc(state.search.produtos)}"></label><span class="record-count">${state.products.length} produtos cadastrados</span></div>${state.products.length?`<div class="table-wrap"><table><thead><tr><th>Código</th><th>Produto</th><th>Categoria</th><th class="amount">Preço</th><th class="amount">Estoque</th><th class="amount">Mínimo</th><th>Situação</th><th class="amount">Ações</th></tr></thead><tbody>${state.products.map(p=>`<tr data-search="${esc(`${p.nome} ${p.categoria}`.toLocaleLowerCase("pt-BR"))}"><td class="muted">${String(p.id).padStart(3,"0")}</td><td class="strong">${esc(p.nome)}</td><td class="muted">${esc(p.categoria)}</td><td class="amount">${money(p.preco)}</td><td class="amount">${p.estoque}</td><td class="amount muted">${p.estoque_minimo}</td><td>${p.ativo?badge(p.estoque<=p.estoque_minimo?"Estoque baixo":"Ativo",p.estoque<=p.estoque_minimo?"amber":""):badge("Inativo","gray")}</td><td><div class="row-actions"><button class="text-action" aria-label="Editar ${esc(p.nome)}" data-action="edit-product" data-id="${p.id}">Editar</button><button class="text-action delete" aria-label="Excluir ${esc(p.nome)}" data-action="delete-product" data-id="${p.id}">Excluir</button></div></td></tr>`).join("")}</tbody></table></div>`:empty("Nenhum produto cadastrado.")}</section>`;
  filterRows(state.search.produtos);
}
function renderCustomers() {
  app.innerHTML=heading("Clientes","Cadastro e consulta dos dados de contato.",`<button class="button primary" data-action="edit-customer">Novo cliente</button>`)+
  `<section class="panel"><div class="toolbar"><label class="search-box">${icon("search")}<input id="search" data-search-type="clientes" aria-label="Buscar cliente" placeholder="Buscar por nome ou e-mail" value="${esc(state.search.clientes)}"></label><span class="record-count">${state.customers.length} clientes cadastrados</span></div>${state.customers.length?`<div class="table-wrap"><table><thead><tr><th>Código</th><th>Cliente</th><th>E-mail</th><th>Telefone</th><th>Situação</th><th class="amount">Ações</th></tr></thead><tbody>${state.customers.map(c=>`<tr data-search="${esc(`${c.nome} ${c.email}`.toLocaleLowerCase("pt-BR"))}"><td class="muted">${String(c.id).padStart(3,"0")}</td><td class="strong">${esc(c.nome)}</td><td class="muted">${esc(c.email)}</td><td class="muted nowrap">${esc(c.telefone)||"—"}</td><td>${badge(c.ativo?"Ativo":"Inativo",c.ativo?"":"gray")}</td><td><div class="row-actions"><button class="text-action" aria-label="Editar ${esc(c.nome)}" data-action="edit-customer" data-id="${c.id}">Editar</button><button class="text-action delete" aria-label="Excluir ${esc(c.nome)}" data-action="delete-customer" data-id="${c.id}">Excluir</button></div></td></tr>`).join("")}</tbody></table></div>`:empty("Nenhum cliente cadastrado.")}</section>`;
  filterRows(state.search.clientes);
}
function filterRows(search) {
  const normalized=search.toLocaleLowerCase("pt-BR").trim();
  document.querySelectorAll("[data-search]").forEach(row=>{row.hidden=!row.dataset.search.includes(normalized);});
}
function renderCart(page) {
  const isSale=page==="venda", cart=state.carts[page], total=state.totals[page];
  const subtotal=cart.reduce((sum,item)=>sum+Number(product(item.produto_id)?.preco||0)*item.quantidade,0);
  const products=activeProducts();
  app.innerHTML=heading(isSale?"Nova venda":"Orçamento",isSale?"Selecione o cliente e inclua os produtos da venda.":"Adicione produtos para calcular o total com desconto.")+
  `<div class="sale-layout"><section class="panel"><div class="panel-heading"><div><h2>${isSale?"Dados da venda":"Itens do orçamento"}</h2><p class="subtitle">${isSale?"O estoque será atualizado ao confirmar.":"Esta consulta não altera o estoque."}</p></div></div>
  ${isSale?`<div class="customer-select"><div class="field"><label for="sale-customer">Cliente</label><select id="sale-customer">${activeCustomers().length?activeCustomers().map(c=>`<option value="${c.id}" ${String(c.id)===String(state.customerId)?"selected":""}>${esc(c.nome)}</option>`).join(""):"<option value=\"\">Cadastre um cliente ativo</option>"}</select></div></div>`:""}
  <form class="item-form" data-form="add-item"><div class="field"><label for="cart-product">Produto</label><select id="cart-product" name="produto_id" required>${products.length?products.map(p=>`<option value="${p.id}">${esc(p.nome)} · ${money(p.preco)} · ${p.estoque} un.</option>`).join(""):"<option value=\"\">Nenhum produto ativo</option>"}</select></div><div class="field"><label for="cart-add-quantity">Quantidade</label><input id="cart-add-quantity" name="quantidade" type="number" min="1" max="1000" step="1" value="1" required></div><button class="button" type="submit" ${products.length?"":"disabled"}>Adicionar</button></form>
  ${cart.length?`<div class="table-wrap"><table><thead><tr><th>Produto</th><th>Quantidade</th><th class="amount">Subtotal</th><th class="amount">Ação</th></tr></thead><tbody>${cart.map(item=>{const p=product(item.produto_id);return `<tr><td><span class="strong">${esc(p?.nome||"Produto indisponível")}</span><br><small class="muted">${money(p?.preco)} por unidade</small></td><td><input class="cart-quantity" data-cart-id="${item.produto_id}" aria-label="Quantidade de ${esc(p?.nome)}" type="number" min="1" max="1000" step="1" value="${item.quantidade}"></td><td class="amount strong">${money(Number(p?.preco||0)*item.quantidade)}</td><td class="amount"><button class="text-action delete" data-action="remove-item" data-id="${item.produto_id}" aria-label="Remover ${esc(p?.nome)}">Remover</button></td></tr>`;}).join("")}</tbody></table></div>`:empty("Nenhum produto adicionado.")}
  </section><aside><section class="panel summary-card"><h2>Resumo do pedido</h2><div class="summary-line"><span>Produtos</span><strong>${cart.length}</strong></div><div class="summary-line"><span>Subtotal</span><strong id="summary-subtotal">${money(subtotal)}</strong></div><div class="field discount-field"><label for="cart-discount">Desconto (%)</label><input id="cart-discount" type="number" min="0" max="100" step="0.01" value="${esc(state.discounts[page])}"><small>De 0% a 100%.</small></div>
  <div class="summary-total"><p>Total ${total===null?"a calcular":"calculado"}</p><strong>${total===null?"—":money(total)}</strong></div>
  <button class="button ${isSale?"":"primary"}" data-action="calculate" ${cart.length?"":"disabled"}>${isSale?"Calcular total":"Gerar orçamento"}</button>
  ${isSale?`<button class="button primary" data-action="sell" ${total!==null&&state.customerId?"":"disabled"}>Confirmar venda</button>`:total!==null?`<button class="button" data-action="transfer-cart">Continuar para venda</button>`:""}
  <p class="summary-note">${total===null?"Calcule o pedido para conferir o total.":"Total calculado com os produtos e o desconto informados."}</p>
  ${isSale&&state.lastSale?`<div class="success-note">Venda #${state.lastSale.venda_id} registrada por <strong>${money(state.lastSale.valor_total)}</strong>. Estoque atualizado.<br><a href="#relatorio" class="button small">Ver no relatório</a></div>`:""}</section></aside></div>`;
}
function renderReport() {
  const report=state.filteredReport||state.report, s=report.resumo;
  app.innerHTML=heading("Relatório de vendas","Consulte as vendas registradas ou filtre por data.",`<button class="button" data-action="refresh-report">Atualizar</button>`)+
  `<div class="stats">${stat("Valor das vendas",money(s.faturamento),"No período selecionado")}${stat("Vendas",s.vendas||0,"Vendas registradas")}${stat("Unidades vendidas",s.unidades||0,"Quantidade total dos itens")}${stat("Descontos",money(s.descontos),"Valor concedido no período")}</div>
  <form class="panel filter-panel filters" data-form="filter"><div class="field"><label for="report-start">Data inicial</label><input id="report-start" type="date" name="inicio" value="${esc(state.filters.inicio)}"></div><div class="field"><label for="report-end">Data final</label><input id="report-end" type="date" name="fim" value="${esc(state.filters.fim)}"></div><button class="button primary" type="submit">Filtrar período</button><button class="button" type="button" data-action="clear-filter">Limpar</button></form>
  <section class="panel"><div class="panel-heading"><h2>Vendas registradas</h2><span class="record-count">${s.vendas||0} resultados</span></div>${salesTable(report.vendas)}</section>`;
}
const resourceInfo = {
  View:{name:"vw_relatorio_vendas",text:"Consolida vendas, clientes e itens em uma linha por venda.",screen:"Relatório de vendas",path:"/api/relatorio"},
  Function:{name:"fn_calcular_total_venda",text:"Recebe o subtotal e o desconto. Retorna o valor final da compra.",screen:"Orçamento",path:"/api/orcamento"},
  Procedure:{name:"sp_baixar_estoque",text:"Recebe um produto e a quantidade vendida. Dá baixa no estoque.",screen:"Nova venda",path:"/api/vendas"},
};
async function loadResources() {
  try{state.resources=await api("/api/recursos");if(state.page==="banco")renderBank();}catch(e){toast(e.message,true);}
}
function renderBank() {
  const selected=state.selectedResource, info=resourceInfo[selected], resources=state.resources;
  const events=(resources?.eventos||[]).filter(e=>e.recurso===selected).slice(0,4);
  app.innerHTML=heading("Banco de dados","Scripts SQL e registros das chamadas executadas pela aplicação.",`<button class="button" data-action="refresh-resources">Atualizar chamadas</button>`)+
  `<div class="resource-tabs" role="group" aria-label="Recursos do PostgreSQL">${Object.keys(resourceInfo).map(key=>`<button class="resource-tab ${key===selected?"selected":""}" aria-pressed="${key===selected}" data-action="select-resource" data-resource="${key}">${key}</button>`).join("")}</div>
  <div class="resource-description"><code>${info.name}</code><p>${info.text}</p></div>
  <div class="integration-path"><span>${info.screen}</span>${icon("arrow")}<span>Python · ${info.path}</span>${icon("arrow")}<span>PostgreSQL · ${selected}</span>${icon("arrow")}<span>Resultado na tela</span></div>
  <div class="code-layout"><section class="panel"><div class="panel-heading"><h2>Código da ${selected}</h2><span class="record-count">SQL / PL/pgSQL</span></div><pre class="code-block"><code>${esc(resources?.scripts[selected]||"Carregando script…")}</code></pre></section><section class="panel"><div class="panel-heading"><div><h2>Chamadas reais</h2><p class="subtitle">Execuções nesta sessão da aplicação</p></div><span class="record-count">${events.length} exibidas</span></div>${events.length?events.map(e=>`<div class="event"><div class="event-head"><strong>${esc(e.tela)}</strong><span class="muted">${hour(e.horario)}</span></div><pre>${esc(e.sql)}</pre><small>Parâmetros recebidos</small><pre>${esc(JSON.stringify(e.parametros,null,2))}</pre><small>Resultado retornado pelo banco</small><pre>${esc(JSON.stringify(e.resultado,null,2))}</pre></div>`).join(""):empty(`Use a tela ${info.screen} e depois atualize as chamadas.`)}</section></div>`;
}
function render() {
  document.querySelectorAll("[data-nav]").forEach(link=>{link.classList.toggle("active",link.dataset.nav===state.page);link.setAttribute("aria-current",link.dataset.nav===state.page?"page":"false");});
  $("#breadcrumb").textContent=names[state.page]; document.title=`${names[state.page]} · Projeto de Banco de Dados`;
  const renders={inicio:renderHome,produtos:renderProducts,clientes:renderCustomers,orcamento:()=>renderCart("orcamento"),venda:()=>renderCart("venda"),relatorio:renderReport,banco:renderBank};
  renders[state.page]();
}
function navigate() {
  const requested=location.hash.slice(1);state.page=names[requested]?requested:"inicio";render();
  if(state.page==="banco")loadResources();
}
function openModal(content) { $("#modal-content").innerHTML=content; if(!modal.open)modal.showModal(); }
function modalHeader(title) {return `<div class="modal-header"><h2>${title}</h2><button class="icon-button" data-action="close-modal" aria-label="Fechar">×</button></div>`;}
function field(label,name,value,type="text",extra="") {return `<div class="field"><label for="edit-${name}">${label}</label><input id="edit-${name}" name="${name}" type="${type}" value="${esc(value)}" ${extra}></div>`;}
function editEntity(type,id) {
  const isProduct=type==="product", entity=(isProduct?state.products:state.customers).find(e=>e.id===Number(id));
  const defaults=isProduct?{nome:"",categoria:"Geral",preco:"",estoque:0,estoque_minimo:5,ativo:true}:{nome:"",email:"",telefone:"",ativo:true};
  const data=entity||defaults;
  openModal(`${modalHeader(`${entity?"Editar":"Novo"} ${isProduct?"produto":"cliente"}`)}<form data-form="entity" data-type="${type}" data-id="${id||""}"><div class="modal-body"><div class="form-grid">${field("Nome","nome",data.nome,"text","required minlength='2' maxlength='120'")}${isProduct?field("Categoria","categoria",data.categoria,"text","required minlength='2' maxlength='60'")+field("Preço (R$)","preco",data.preco,"number","required min='0.01' max='1000000' step='0.01'")+field("Estoque atual","estoque",data.estoque,"number","required min='0' max='1000000' step='1'")+field("Estoque mínimo","estoque_minimo",data.estoque_minimo,"number","required min='0' max='1000000' step='1'"):field("E-mail","email",data.email,"email","required maxlength='160'")+field("Telefone","telefone",data.telefone,"tel","maxlength='30'")}<div class="field checkbox full"><input id="edit-ativo" name="ativo" type="checkbox" ${data.ativo?"checked":""}><label for="edit-ativo">${isProduct?"Produto disponível para novas vendas":"Cliente ativo para novas vendas"}</label></div></div><p class="modal-error" id="modal-error" role="alert"></p></div><div class="modal-footer"><button type="button" class="button" data-action="close-modal">Cancelar</button><button type="submit" class="button primary">Salvar ${isProduct?"produto":"cliente"}</button></div></form>`);
}
function deleteEntity(type,id) {
  const isProduct=type==="product", item=(isProduct?state.products:state.customers).find(e=>e.id===Number(id));
  openModal(`${modalHeader("Excluir cadastro")}<div class="modal-body"><p>Excluir <strong>${esc(item?.nome)}</strong>?</p><p class="subtitle" style="margin-top:8px">Cadastros vinculados a vendas devem ser inativados pelo formulário de edição para preservar o histórico.</p><p class="modal-error" id="modal-error" role="alert"></p></div><div class="modal-footer"><button class="button" data-action="close-modal">Cancelar</button><button class="button danger" data-action="confirm-delete" data-type="${type}" data-id="${id}">Excluir cadastro</button></div>`);
}
async function showDetails(id) {
  const {venda:v,itens}=await api(`/api/vendas/${id}`);
  openModal(`${modalHeader(`Venda #${String(v.venda_id).padStart(3,"0")}`)}<div class="modal-body"><div class="detail-summary"><div><h3>${esc(v.cliente_nome)}</h3><p>${day(v.data_venda)} · ${hour(v.data_venda)}</p></div><strong>${money(v.valor_total)}</strong></div><div class="table-wrap"><table><thead><tr><th>Produto</th><th>Qtd.</th><th class="amount">Subtotal</th></tr></thead><tbody>${itens.map(i=>`<tr><td>${esc(i.produto_nome)}</td><td>${i.quantidade}</td><td class="amount">${money(i.quantidade*Number(i.preco_unitario))}</td></tr>`).join("")}</tbody></table></div><div class="summary-line"><span>Subtotal</span><strong>${money(v.subtotal)}</strong></div><div class="summary-line"><span>Desconto (${Number(v.desconto_percentual)}%)</span><strong>${money(v.valor_desconto)}</strong></div></div><div class="modal-footer"><button class="button" data-action="close-modal">Fechar</button></div>`);
}
async function perform(action) {
  if(state.pending)return;state.pending=true;
  const controls=[...document.querySelectorAll("button,input,select")].map(el=>[el,el.disabled]);controls.forEach(([el])=>{el.disabled=true;});
  try{await action();}catch(e){if(modal.open&&$("#modal-error"))$("#modal-error").textContent=e.message;else toast(e.message,true);}
  finally{state.pending=false;controls.forEach(([el,disabled])=>{if(el.isConnected)el.disabled=disabled;});}
}
function invalidate() {state.totals[state.page]=null;state.lastSale=null;}
function invalidateDisplayedTotal() {
  invalidate();
  const heading=$(".summary-total p"), value=$(".summary-total strong"), note=$(".summary-note");
  if(heading)heading.textContent="Total a calcular";if(value)value.textContent="—";if(note)note.textContent="Calcule o pedido para conferir o valor final.";
  $("[data-action='sell']")?.setAttribute("disabled","");$("[data-action='transfer-cart']")?.remove();$(".success-note")?.remove();
}
document.addEventListener("click",event=>{
  const button=event.target.closest("[data-action]");if(!button||state.pending)return;
  const {action,id,type,resource}=button.dataset;
  if(action==="close-modal"){modal.close();return;}
  if(action==="edit-product"){editEntity("product",id);return;}
  if(action==="edit-customer"){editEntity("customer",id);return;}
  if(action==="delete-product"){deleteEntity("product",id);return;}
  if(action==="delete-customer"){deleteEntity("customer",id);return;}
  if(action==="remove-item"){state.carts[state.page]=state.carts[state.page].filter(i=>i.produto_id!==Number(id));invalidate();render();return;}
  if(action==="select-resource"){state.selectedResource=resource;renderBank();return;}
  if(action==="transfer-cart"){state.carts.venda=state.carts.orcamento.map(i=>({...i}));state.discounts.venda=state.discounts.orcamento;state.totals.venda=state.totals.orcamento;state.lastSale=null;location.hash="venda";return;}
  perform(async()=>{
    if(action==="calculate"){
      const page=state.page; const result=await api("/api/orcamento","POST",{itens:state.carts[page],desconto:state.discounts[page]});
      state.totals[page]=result.total;render();toast("Total calculado. Confira o resumo do pedido.");
    } else if(action==="sell"){
      const result=await api("/api/vendas","POST",{cliente_id:Number(state.customerId),itens:state.carts.venda,desconto:state.discounts.venda});
      state.lastSale=result;state.carts.venda=[];state.totals.venda=null;state.filteredReport=null;await refresh();render();toast(`Venda #${result.venda_id} registrada. Estoque atualizado.`);
    } else if(action==="detail")await showDetails(id);
    else if(action==="confirm-delete"){
      await api(`/api/${type==="product"?"produtos":"clientes"}/${id}`,"DELETE");await refresh();state.totals={orcamento:null,venda:null};modal.close();render();toast("Cadastro excluído.");
    } else if(action==="refresh-resources")await loadResources();
    else if(action==="refresh-report"||action==="clear-filter"){
      if(action==="clear-filter")state.filters={inicio:"",fim:""};
      const params=new URLSearchParams(state.filters);state.filteredReport=await api(`/api/relatorio?${params}`);renderReport();
    }
  });
});
document.addEventListener("submit",event=>{
  const form=event.target.closest("form[data-form]");if(!form)return;event.preventDefault();if(state.pending)return;
  const data=Object.fromEntries(new FormData(form));
  if(form.dataset.form==="add-item"){
    const id=Number(data.produto_id),qty=Number(data.quantidade);if(!id||!Number.isInteger(qty)||qty<1||qty>1000){toast("Escolha um produto e uma quantidade de 1 a 1000.",true);return;}
    const item=state.carts[state.page].find(i=>i.produto_id===id);
    if(item){if(item.quantidade+qty>1000){toast("O limite é de 1000 unidades por produto.",true);return;}item.quantidade+=qty;}else state.carts[state.page].push({produto_id:id,quantidade:qty});invalidate();render();return;
  }
  perform(async()=>{
    if(form.dataset.form==="entity"){
      data.ativo=form.elements.ativo.checked;const id=form.dataset.id;const isProduct=form.dataset.type==="product";
      await api(`/api/${isProduct?"produtos":"clientes"}${id?`/${id}`:""}`,id?"PUT":"POST",data);
      await refresh();state.totals={orcamento:null,venda:null};modal.close();render();toast("Cadastro salvo com sucesso.");
    } else if(form.dataset.form==="filter"){
      state.filters=data;state.filteredReport=await api(`/api/relatorio?${new URLSearchParams(data)}`);renderReport();
    }
  });
});
document.addEventListener("input",event=>{
  if(event.target.dataset.searchType){state.search[event.target.dataset.searchType]=event.target.value;filterRows(event.target.value);}
  if(state.pending)return;const target=event.target;
  if(target.id==="cart-discount"){state.discounts[state.page]=target.value;invalidateDisplayedTotal();}
  if(target.dataset.cartId){
    const value=Number(target.value), item=state.carts[state.page].find(i=>i.produto_id===Number(target.dataset.cartId));
    if(Number.isInteger(value)&&value>=1&&value<=1000){item.quantidade=value;target.closest("tr").querySelector(".amount.strong").textContent=money(Number(product(item.produto_id)?.preco||0)*value);$("#summary-subtotal").textContent=money(state.carts[state.page].reduce((s,i)=>s+Number(product(i.produto_id)?.preco||0)*i.quantidade,0));}
    invalidateDisplayedTotal();
  }
});
document.addEventListener("change",event=>{
  if(state.pending)return;const target=event.target;
  if(target.id==="sale-customer")state.customerId=target.value;
  if(target.dataset.cartId){const value=Number(target.value);if(!Number.isInteger(value)||value<1||value>1000){toast("Informe uma quantidade de 1 a 1000.",true);target.value=state.carts[state.page].find(i=>i.produto_id===Number(target.dataset.cartId)).quantidade;}}
});
window.addEventListener("hashchange",navigate);
async function initialize() {
  try{
    await api("/api/status");$("#connection-dot").classList.add("connected");$("#connection-label").textContent="Banco conectado";
    await refresh();navigate();
  }catch(e){$("#connection-dot").classList.add("offline");$("#connection-label").textContent="Banco indisponível";app.innerHTML=`<div class="error-banner">${esc(e.message)}<p class="subtitle">Inicie o projeto pelo arquivo iniciar.bat ou confira DATABASE_URL.</p></div>`;}
}
initialize();
