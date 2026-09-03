export function flatten(value){
    if (!Array.isArray(value)) return [value];
    return value.reduce((items, item) => items.concat(flatten(item)), []);
}

export function dimensions(value){
    let shape = [], current = value;
    while (Array.isArray(current)){
        shape.push(current.length);
        current = current.length ? current[0] : null;
    }
    return shape;
}

export function rank(value){
    return dimensions(value).length;
}
