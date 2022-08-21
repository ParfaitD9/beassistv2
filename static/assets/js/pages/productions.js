$(document).ready((e) => {
  document.querySelector("a.nav-link.active").classList.remove("active");
  document.querySelectorAll("a.nav-link")[4].classList.add("active");
  fillProductions();
  load_packs();
  /*
  setTimeout((t) => {
    document.querySelectorAll("a.delete").forEach((el) => {
      el.addEventListener("click", (t) => {
        let row = el.parentElement.parentElement.parentElement.parentElement;
        axios
          .post(`/api/v1/production/delete/${row.id}`)
          .then((res) => {
            if (res.data.success) {
              row.remove();
            }
          })
          .catch((err) => console.log(err));
      });
    });

    document.querySelectorAll("a.send").forEach((el) => {
      el.addEventListener("click", (t) => {
        let row = el.parentElement.parentElement.parentElement.parentElement;
        document
          .querySelector("form#sendProdModalForm")
          .querySelector("input#ref").value = row.id;
      });
    });
  }, 1000);
  */
});

function createRow(production) {
  let row = document.createElement("tr");
  row.id = production.pk;
  let text = production.packs
    .map((p) => p.name)
    .join(",")
    .slice(0, 30);
  console.log(
    production.packs
      .map((p) => {
        return p.name;
      })
      .join(",")
  );
  console.log(text);
  row.innerHTML = `
    <td>
      <div class="d-flex px-2 py-1">
          <div class="d-flex flex-column justify-content-center">
          <h6 class="mb-0 text-sm">${production.name}</h6>
          </div>
      </div>
      </td>
      <td>
      <p class="text-xs font-weight-bold mb-0">${text} ...</p>
      <p class="text-xs text-secondary mb-0">${production.packs.length} contrats</p>
      </td>
      <td class="text-sm">
          <span class="font-weight-bold text-center align-middle">${production.price} $</span>
      </td>
      <td class="align-middle text-center">
          <a
              href="javascript:;"
              class="nav-link text-body p-0"
              id="dropdownProdMenuButton-${production.pk}"
              data-bs-toggle="dropdown"
              aria-expanded="false"
          >
              <i class="fa fa-ellipsis-h cursor-pointer"></i>
          </a>
          <ul
              class="dropdown-menu dropdown-menu-end px-2 py-3 me-sm-n4"
              aria-labelledby="dropdownProdMenuButton-${production.pk}"
          >
              <li>
                  <a class="font-weight-bold dropdown-item border-radius-md disabled">
                      Facturer cette production
                  </a>
              </li>
              <li>
                  <a class="font-weight-bold dropdown-item border-radius-md disabled">
                      Modifier cette production
                  </a>
              </li>
              <li>
                  <a class="font-weight-bold dropdown-item border-radius-md" onclick="production_send(event)" data-bs-toggle="modal" data-bs-target="#sendProdModal">
                      Envoyer cette production
                  </a>
              </li>
              <li>
                  <a class="font-weight-bold dropdown-item border-radius-md" onclick="production_delete(event)">
                      Supprimer cette production
                  </a>
              </li>
          </ul>
      </td>
      `;

  return row;
}

function fillProductions() {
  let table = document.querySelector("tbody#productionsTbody");
  axios
    .get("/api/v1/productions")
    .then((res) => {
      if (res.data.success) {
        table?.querySelectorAll("tr").forEach((el) => {
          el.remove();
        });

        res.data.data.forEach((element) => {
          table?.appendChild(createRow(element));
        });
      }
    })
    .catch((err) => console.log(err));
}

$("form#addProdModalForm").submit((e) => {
  e.preventDefault();
  let data = new FormData(e.target);
  axios
    .post("/api/v1/production/create", data)
    .then((res) => {
      showModalAlert("addProdModal", res);
      if (res.data.success) {
        document
          .querySelector("tbody#productionsTbody")
          .prepend(createRow(res.data.data));
      }
    })
    .catch((err) => console.log(err));
});

$("form#sendProdModalForm").submit((e) => {
  e.preventDefault();
  let data = new FormData(e.target);
  let pk = data.get("pk");
  console.log("pk est ", pk);
  data.delete("pk");
  showModalAlert("sendProdModal", {
    data: {
      success: true,
      message:
        "Facturation et envoi en cours. Ne fermez pas le formulaire, veuillez patienter ...",
    },
  });
  axios
    .post(`/api/v1/production/send/${pk}`, data)
    .then((res) => {
      showModalAlert("sendProdModal", res);
      window.alert(
        `Liste de facturation ${res.data.data.name} facturé et envoyé`
      );
      e.target.reset();
    })
    .catch((err) => console.log(err));
});

function production_send(e) {
  let row = e.target.parentElement.parentElement.parentElement.parentElement;
  document
    .querySelector("form#sendProdModalForm")
    .querySelector("input#ref").value = row.id;
}

function production_delete(e) {
  let row = e.target.parentElement.parentElement.parentElement.parentElement;
  axios
    .post(`/api/v1/production/delete/${row.id}`)
    .then((res) => {
      if (res.data.success) {
        row.remove();
      } else {
        window.alert(res.data.message);
      }
    })
    .catch((err) => console.log(err));
}
